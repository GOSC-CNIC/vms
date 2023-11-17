from urllib.parse import quote as urlquote

from django.utils.translation import gettext as _
from django.http import FileResponse
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.serializers import DecimalField

from service.managers import (
    VmServiceApplyManager, OrganizationApplyManager,
    ServicePrivateQuotaManager, ServiceShareQuotaManager, ServiceManager,
)
from service.models import ServiceConfig
from vo.managers import VoManager, VoMemberManager, VoMember
from utils import storagers
from utils import time
from utils.model import OwnerType
from core import errors as exceptions
from api.serializers import serializers
from api.viewsets import CustomGenericViewSet, serializer_error_msg
from servers.managers import ServerManager, DiskManager
from order.managers import OrderManager
from bill.models import CashCoupon
from bill.managers import PaymentManager


class ApplyOrganizationHandler:
    @staticmethod
    def get_list_queryset(request, is_admin: bool = False):
        """
        获取查询集

        :param request:
        :param is_admin: True: 有管理权限的申请记录查询集；False: 用户自己的申请记录查询集；
        """
        deleted = request.query_params.get('deleted', None)
        status = request.query_params.getlist('status', None)
        if not status or status == ['']:
            status = None
        if isinstance(status, list):
            if not set(status).issubset(set(OrganizationApplyManager.model.Status.values)):
                raise exceptions.InvalidArgument(message=_('参数"status"包含无效的值'))

        if deleted:
            deleted = deleted.lower()
            if deleted == 'true':
                deleted = True
            elif deleted == 'false':
                deleted = False
            else:
                deleted = None

        if is_admin:
            return OrganizationApplyManager().admin_filter_apply_queryset(
                deleted=deleted, status=status)
        else:
            return OrganizationApplyManager().filter_user_apply_queryset(
                user=request.user, deleted=deleted, status=status)

    @staticmethod
    def list_apply(view, request, kwargs):
        """
        list user机构加入申请
        """
        try:
            queryset = ApplyOrganizationHandler.get_list_queryset(request=request)
            paginator = view.pagination_class()
            applies = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.ApplyOrganizationSerializer(instance=applies, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

    @staticmethod
    def admin_list_apply(view, request, kwargs):
        """
        管理员list机构加入申请
        """
        if not request.user.is_federal_admin():
            return view.exception_response(
                exc=exceptions.AccessDenied(message=_('你没有访问权限，需要联邦管理员权限')))
        try:
            queryset = ApplyOrganizationHandler.get_list_queryset(request=request, is_admin=True)
            paginator = view.pagination_class()
            applies = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.ApplyOrganizationSerializer(instance=applies, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

    @staticmethod
    def create_apply(view, request, kwargs):
        """
        提交一个机构/数据中心创建申请
        """
        oa_mgr = OrganizationApplyManager()
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        count = oa_mgr.get_in_progress_apply_count(user=request.user)
        if count >= 6:
            return view.exception_response(exceptions.TooManyApply())

        try:
            apply = oa_mgr.create_apply(data=serializer.validated_data, user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        rdata = serializers.ApplyOrganizationSerializer(instance=apply).data
        return Response(data=rdata)

    @staticmethod
    def apply_action(view, request, kwargs):
        """
            cancel：取消申请
            pending：挂起申请（审核中）
            reject：拒绝
            pass：通过
            delete: 删除
        """
        _action = kwargs.get('action', '').lower()
        if _action == 'pending':
            return ApplyOrganizationHandler.pending_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'cancel':
            return ApplyOrganizationHandler.cancel_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'reject':
            return ApplyOrganizationHandler.reject_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'pass':
            return ApplyOrganizationHandler.pass_apply(view=view, request=request, kwargs=kwargs)

        return view.exception_response(
            exc=exceptions.BadRequest(message=_('不支持操作命令"{action}"').format(action=_action)))

    @staticmethod
    def pending_apply(view, request, kwargs):
        """
        挂起一个机构/数据中心创建申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = OrganizationApplyManager().pending_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyOrganizationSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def cancel_apply(view, request, kwargs):
        """
        取消一个机构/数据中心创建申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = OrganizationApplyManager().cancel_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyOrganizationSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def pass_apply(view, request, kwargs):
        """
        审核通过一个机构/数据中心创建申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = OrganizationApplyManager().pass_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyOrganizationSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def reject_apply(view, request, kwargs):
        """
        审核拒绝一个机构/数据中心创建申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = OrganizationApplyManager().reject_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyOrganizationSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def delete_apply(view, request, kwargs):
        """
        软删除一个机构/数据中心创建申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            OrganizationApplyManager().delete_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(status=204)


class ApplyVmServiceHandler:
    @staticmethod
    def get_list_queryset(request, is_admin: bool = False):
        """
        获取查询集

        :param request:
        :param is_admin: True: 有管理权限的申请记录查询集；False: 用户自己的申请记录查询集；

        :raises: Error
        """
        organization_id = request.query_params.get('organization', None)
        deleted = request.query_params.get('deleted', None)
        if deleted:
            deleted = deleted.lower()
            if deleted == 'true':
                deleted = True
            elif deleted == 'false':
                deleted = False
            else:
                deleted = None

        status = request.query_params.getlist('status', None)
        if not status or status == ['']:
            status = None
        if isinstance(status, list):
            if not set(status).issubset(set(VmServiceApplyManager.model.Status.values)):
                raise exceptions.InvalidArgument(message=_('参数"status"包含无效的值'))

        if is_admin:
            return VmServiceApplyManager().admin_filter_apply_queryset(
                deleted=deleted, organization_id=organization_id, status=status)
        else:
            return VmServiceApplyManager().filter_user_apply_queryset(
                user=request.user, deleted=deleted, organization_id=organization_id, status=status)

    @staticmethod
    def list_apply(view, request, kwargs):
        """
        list user云主机服务接入申请
        """
        try:
            queryset = ApplyVmServiceHandler.get_list_queryset(request=request)
            paginator = view.pagination_class()
            applies = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.ApplyVmServiceSerializer(instance=applies, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

    @staticmethod
    def admin_list_apply(view, request, kwargs):
        """
        管理员list云主机服务接入申请
        """
        if not request.user.is_federal_admin():
            return view.exception_response(
                exc=exceptions.AccessDenied(message=_('你没有访问权限，需要联邦管理员权限')))
        try:
            queryset = ApplyVmServiceHandler.get_list_queryset(request=request, is_admin=True)
            paginator = view.pagination_class()
            applies = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = serializers.ApplyVmServiceSerializer(instance=applies, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

    @staticmethod
    def create_apply(view, request, kwargs):
        """
        提交一个服务接入申请
        """
        vsa_mgr = VmServiceApplyManager()
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        count = vsa_mgr.get_in_progress_apply_count(user=request.user)
        if count >= 6:
            return view.exception_response(exceptions.TooManyApply())

        try:
            apply = vsa_mgr.create_apply(data=serializer.validated_data, user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        rdata = serializers.ApplyVmServiceSerializer(instance=apply).data
        return Response(data=rdata)

    @staticmethod
    def apply_action(view, request, kwargs):
        """
            cancel：取消申请
            pending：挂起申请（审核中）
            first_pass：初审通过
            first_reject：初审拒绝
            test：测试
            reject：拒绝
            pass：通过
        """
        _action = kwargs.get('action', '').lower()
        if _action == 'cancel':
            return ApplyVmServiceHandler.cancel_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'pending':
            return ApplyVmServiceHandler.pending_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'first_reject':
            return ApplyVmServiceHandler.first_reject_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'first_pass':
            return ApplyVmServiceHandler.first_pass_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'test':
            return ApplyVmServiceHandler.test_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'reject':
            return ApplyVmServiceHandler.reject_apply(view=view, request=request, kwargs=kwargs)
        elif _action == 'pass':
            return ApplyVmServiceHandler.pass_apply(view=view, request=request, kwargs=kwargs)

        return view.exception_response(
            exc=exceptions.BadRequest(message=_('不支持操作命令"{action}"').format(action=_action)))

    @staticmethod
    def cancel_apply(view, request, kwargs):
        """
        取消一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = VmServiceApplyManager().cancel_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def pending_apply(view, request, kwargs):
        """
        挂起一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = VmServiceApplyManager().pending_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def first_reject_apply(view, request, kwargs):
        """
        初审拒绝一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = VmServiceApplyManager().first_reject_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def first_pass_apply(view, request, kwargs):
        """
        初审通过一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = VmServiceApplyManager().first_pass_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def test_apply(view, request, kwargs):
        """
        测试一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply, test_msg = VmServiceApplyManager().test_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data={
            'ok': False if test_msg else True,
            'message': test_msg,
            'apply': serializer.data
        })

    @staticmethod
    def reject_apply(view, request, kwargs):
        """
        拒绝一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = VmServiceApplyManager().reject_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def pass_apply(view, request, kwargs):
        """
        通过一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            apply = VmServiceApplyManager().pass_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        serializer = serializers.ApplyVmServiceSerializer(apply)
        return Response(data=serializer.data)

    @staticmethod
    def delete_apply(view, request, kwargs):
        """
        软删除一个申请
        """
        pk = kwargs.get(view.lookup_field)
        try:
            VmServiceApplyManager().delete_apply(_id=pk, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(status=204)


class MediaHandler:
    @staticmethod
    def media_upload(view, request, kwargs):
        paths = kwargs.get(view.lookup_field, '').rsplit('/', maxsplit=1)
        if len(paths) == 2:
            storage_to, filename = paths
        else:
            storage_to, filename = '', paths[-1]

        request.upload_handlers = [
            storagers.Md5TemporaryFileUploadHandler(request=request),
            storagers.Md5MemoryFileUploadHandler(request=request)
        ]

        content_md5 = view.request.headers.get('Content-MD5', '')
        if not content_md5:
            return view.exception_response(exc=exceptions.InvalidDigest())

        content_length = request.headers.get('content-length')
        if not content_length:
            return view.exception_response(
                exc=exceptions.BadRequest(
                    message='header "Content-Length" is required'))

        try:
            content_length = int(content_length)
        except (ValueError, TypeError):
            raise exceptions.BadRequest(
                message='header "Content-Length" is invalid')

        try:
            request.parser_context['kwargs']['filename'] = filename
            put_data = request.data
        except Exception as exc:
            return view.exception_response(exceptions.Error.from_error(exc))

        file = put_data.get('file')
        if not file:
            return view.exception_response(
                exc=exceptions.BadRequest(message='Request body is empty.'))

        if content_length != file.size:
            return view.exception_response(
                exc=exceptions.BadRequest(
                    message='The length of body not same header "Content-Length"'))

        if content_md5 != file.file_md5:
            return view.exception_response(
                exc=exceptions.BadDigest())

        return MediaHandler._storage_media(view=view, subpath=storage_to,
                                           filename=filename, file=file)

    @staticmethod
    def _storage_media(view, subpath: str, filename: str, file):
        if storagers.LogoFileStorager.is_start_prefix(sub_path=subpath):
            filename = storagers.LogoFileStorager.storage_filename(filename=filename, md5=file.file_md5)
            storager = storagers.LogoFileStorager(filename=filename)
        elif storagers.CertificationFileStorager.is_start_prefix(sub_path=subpath):
            filename = storagers.CertificationFileStorager.storage_filename(filename=filename, md5=file.file_md5)
            storager = storagers.CertificationFileStorager(filename=filename)
        else:
            storager = storagers.MediaFileStorager(filename=filename, storage_to=subpath)

        try:
            storager.save_file(file)
        except Exception as exc:
            storager.delete()
            return view.exception_response(exc)

        api_path = reverse('api:media-detail', kwargs={'url_path': storager.relative_path()})
        return Response(data={'url_path': api_path})

    @staticmethod
    def media_download(view, request, kwargs):
        path = kwargs.get(view.lookup_field, '')
        paths = path.rsplit('/', maxsplit=1)
        if len(paths) == 2:
            storage_to, filename = paths
        else:
            storage_to, filename = '', paths[-1]

        if not bool(request.user and request.user.is_authenticated):
            if not (storage_to == 'logo' or storage_to.startswith('logo/')):
                return view.exception_response(exceptions.AccessDenied(message='未认证'))

        return MediaHandler.media_download_response(
            view=view, subpath=storage_to, filename=filename)

    @staticmethod
    def media_download_response(view, subpath: str, filename: str):
        storager = storagers.MediaFileStorager(
            filename=filename, storage_to=subpath)

        if not storager.is_exists():
            return view.exception_response(exc=exceptions.NotFound())

        filesize = storager.size()
        file_generator = storager.get_file_generator()
        last_modified = time.time_to_gmt(storager.last_modified_time())

        filename = urlquote(filename)  # 中文文件名需要
        response = FileResponse(file_generator)
        response['Content-Length'] = filesize
        response['Content-Type'] = 'application/octet-stream'  # 注意格式
        response['Content-Disposition'] = f"attachment;filename*=utf-8''{filename}"  # 注意filename 这个是下载后的名字
        response['Cache-Control'] = 'max-age=20'

        if last_modified:
            response['Last-Modified'] = last_modified

        return response


class VmServiceHandler:
    @staticmethod
    def get_user_perm_service(_id, user):
        """
        :raises: Error
        """
        service = ServiceManager().get_service_by_id(_id)
        if service is None:
            raise exceptions.ServiceNotExist()

        if not service.user_has_perm(user):
            raise exceptions.AccessDenied(message=_('你没有此服务的管理权限'))

        return service

    @staticmethod
    def get_private_quota(view, request, kwargs):
        """
        查询服务私有配额
        """
        try:
            service = VmServiceHandler.get_user_perm_service(
                _id=kwargs.get(view.lookup_field), user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        try:
            quota = ServicePrivateQuotaManager().get_quota(service=service)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        rdata = serializers.VmServicePrivateQuotaSerializer(instance=quota).data
        return Response(data=rdata)

    @staticmethod
    def change_private_quota(view, request, kwargs):
        """
        修改服务私有配额
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        try:
            service = VmServiceHandler.get_user_perm_service(
                _id=kwargs.get(view.lookup_field), user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        data = serializer.validated_data
        private_ip_total = data.get('private_ip_total')
        public_ip_total = data.get('public_ip_total')
        vcpu_total = data.get('vcpu_total')
        ram_total = data.get('ram_total')
        disk_size_total = data.get('disk_size_total')

        try:
            quota = ServicePrivateQuotaManager().update(
                service=service, vcpus=vcpu_total, ram_gib=ram_total, disk_size=disk_size_total,
                public_ip=public_ip_total, private_ip=private_ip_total, only_increase=True)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        rdata = serializers.VmServicePrivateQuotaSerializer(instance=quota).data
        return Response(data=rdata)

    @staticmethod
    def get_share_quota(view, request, kwargs):
        """
        查询服务共享配额
        """
        try:
            service = VmServiceHandler.get_user_perm_service(
                _id=kwargs.get(view.lookup_field), user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        try:
            quota = ServiceShareQuotaManager().get_quota(service=service)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        rdata = serializers.VmServiceShareQuotaSerializer(instance=quota).data
        return Response(data=rdata)

    @staticmethod
    def change_share_quota(view, request, kwargs):
        """
        修改服务共享配额
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        try:
            service = VmServiceHandler.get_user_perm_service(
                _id=kwargs.get(view.lookup_field), user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        data = serializer.validated_data
        private_ip_total = data.get('private_ip_total')
        public_ip_total = data.get('public_ip_total')
        vcpu_total = data.get('vcpu_total')
        ram_total = data.get('ram_total')
        disk_size_total = data.get('disk_size_total')

        try:
            quota = ServiceShareQuotaManager().update(
                service=service, vcpus=vcpu_total, ram_gib=ram_total, disk_size=disk_size_total,
                public_ip=public_ip_total, private_ip=private_ip_total, only_increase=True)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        rdata = serializers.VmServiceShareQuotaSerializer(instance=quota).data
        return Response(data=rdata)

    @staticmethod
    def list_services(view, request, kwargs):
        """
        list接入服务provider
        """
        org_id = request.query_params.get('org_id', None)
        center_id = request.query_params.get('center_id', None)
        status = request.query_params.get('status', None)

        if status is not None:
            if status not in ServiceConfig.Status.values:
                return view.exception_response(
                    exceptions.InvalidArgument(message=_('服务单元服务状态查询参数值无效'), code='InvalidStatus')
                )

        service_qs = ServiceManager().filter_service(org_id=org_id, center_id=center_id, status=status)
        return view.paginate_service_response(request=request, qs=service_qs)


class VoHandler:
    @staticmethod
    def list_vo(view: CustomGenericViewSet, request, kwargs):
        _owner = request.query_params.get('owner', None)
        _member = request.query_params.get('member', None)
        _name = request.query_params.get('name', None)

        if _owner is not None:
            _owner = True
        if _member is not None:
            _member = True

        try:
            if view.is_as_admin_request(request=request):
                queryset = VoManager().get_admin_vo_queryset(
                    user=request.user, owner=_owner, member=_member, name=_name
                )
            else:
                queryset = VoManager().get_user_vo_queryset(
                    user=request.user, owner=_owner, member=_member, name=_name
                )

            paginator = view.pagination_class()
            vos = paginator.paginate_queryset(request=request, queryset=queryset)
            serializer = view.get_serializer(instance=vos, many=True)
            response = paginator.get_paginated_response(data=serializer.data)
            return response
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

    @staticmethod
    def create(view, request, kwargs):
        """
        创建一个组
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        data = serializer.validated_data
        name = data.get('name')
        company = data.get('company')
        description = data.get('description')

        try:
            vo = VoManager().create_vo(name=name, company=company, description=description, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data=view.get_serializer(instance=vo).data)

    @staticmethod
    def delete_vo(view, request, kwargs):
        vo_id = kwargs.get(view.lookup_field)
        try:
            VoManager().delete_vo(vo_id=vo_id, admin_user=request.user)
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

        return Response(status=204)

    @staticmethod
    def update_vo(view, request, kwargs):
        vo_id = kwargs.get(view.lookup_field)
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        data = serializer.validated_data
        name = data.get('name')
        company = data.get('company')
        description = data.get('description')

        try:
            vo = VoManager().update_vo(vo_id=vo_id, admin_user=request.user, name=name,
                                       company=company, description=description)
            return Response(data=serializers.VoSerializer(instance=vo).data)
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

    @staticmethod
    def vo_add_members(view, request, kwargs):
        vo_id = kwargs.get(view.lookup_field)
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        usernames = serializer.validated_data.get('usernames', [])
        try:
            success_members, failed_usernames = VoManager().add_members(
                vo_id=vo_id, usernames=usernames, admin_user=request.user)
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

        members = serializers.VoMemberSerializer(success_members, many=True).data
        return Response(data={'success': members, 'failed': failed_usernames})

    @staticmethod
    def vo_list_members(view, request, kwargs):
        vo_id = kwargs.get(view.lookup_field)
        try:
            vo, members = VoManager().get_vo_members_queryset(vo_id=vo_id, user=request.user)
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

        data = view.get_serializer(members, many=True).data
        return Response(data={
            'members': data, 'owner': {'id': vo.owner.id, 'username': vo.owner.username}})

    @staticmethod
    def vo_remove_members(view, request, kwargs):
        vo_id = kwargs.get(view.lookup_field)
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        usernames = serializer.validated_data.get('usernames', [])
        try:
            VoManager().remove_members(vo_id=vo_id, usernames=usernames, admin_user=request.user)
        except Exception as exc:
            return view.exception_response(exc=exceptions.convert_to_error(exc))

        return Response(status=204)

    @staticmethod
    def vo_members_role(view, request, kwargs):
        member_id = kwargs.get('member_id')
        role = kwargs.get('role')
        if not role:
            raise exceptions.BadRequest(message=_('"role"的值无效'))

        try:
            member = VoMemberManager().change_member_role(
                member_id=member_id, role=role, admin_user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        return Response(data=serializers.VoMemberSerializer(member).data)

    @staticmethod
    def vo_statistic(view, request, kwargs):
        vo_id = kwargs.get(view.lookup_field)
        user = request.user
        try:
            vo, member = VoManager().get_has_read_perm_vo(vo_id=vo_id, user=request.user)
            vo_member_qs = VoMemberManager().get_vo_members_queryset(vo_id=vo_id)
            vo_member_count = vo_member_qs.count() + 1

            # 组角色
            if vo.owner_id == user.id:
                my_vo_role = 'owner'
            else:
                vmb = VoMember.objects.filter(vo_id=vo_id, user_id=user.id).first()
                my_vo_role = vmb.role

            vo_servers = ServerManager().get_vo_servers_queryset(vo_id=vo_id)
            vo_servers_count = vo_servers.count()

            vo_orders = OrderManager().filter_order_queryset(
                vo_id=vo_id, resource_type='', order_type='', status='', time_start=None, time_end=None)
            vo_orders_count = vo_orders.count()

            coupons_qs = CashCoupon.objects.filter(
                vo_id=vo_id, owner_type=OwnerType.VO.value,
                status=CashCoupon.Status.AVAILABLE.value
            )
            vo_coupons_count = coupons_qs.count()

            vo_balance = PaymentManager().get_vo_point_account(vo_id=vo_id)
            vo_disk_qs = DiskManager().get_vo_disks_queryset(vo_id=vo_id)
            vo_disk_count = vo_disk_qs.count()
            data = {
                'vo': {'id': vo.id, 'name': vo.name},
                'my_role': my_vo_role,
                'member_count': vo_member_count,
                'server_count': vo_servers_count,
                'disk_count': vo_disk_count,
                'order_count': vo_orders_count,
                'coupon_count': vo_coupons_count,
                'balance': DecimalField(max_digits=10, decimal_places=2).to_representation(vo_balance.balance)
            }
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data=data)
