from decimal import Decimal
from datetime import datetime

from django.utils.translation import gettext as _
from django.db import transaction
from django.conf import settings
from django.db.models import TextChoices
from rest_framework.response import Response

from core import errors as exceptions
from core.quota import QuotaAPI
from core import request as core_request
from core import site_configs_manager
from apps.servers.managers import ServiceManager
from apps.servers.models import Server, Flavor
from apps.servers.managers import ServerManager, ServerArchiveManager, DiskManager, ResourceActionLogManager
from apps.servers import serializers, format_who_action_str
from apps.api import paginations
from apps.api.viewsets import CustomGenericViewSet, serializer_error_msg
from apps.api import request_logger
from apps.vo.managers import VoManager
from apps.vo.models import VirtualOrganization
from core.adapters import inputs
from core.adapters.client import get_service_client
from utils.model import PayType, OwnerType
from utils.time import iso_utc_to_datetime
from apps.order.deliver_resource import OrderResourceDeliverer
from apps.order.models import ResourceType, Order
from apps.order.managers import OrderManager, ServerConfig, OrderPaymentManager
from apps.app_wallet.managers import PaymentManager
from apps.servers.handlers.disk_handler import DiskHandler


PAY_APP_ID = site_configs_manager.get_pay_app_id(settings, check_valid=True)


def str_to_true_false(val: str):
    if not isinstance(val, str):
        return val

    if val.lower() == 'true':
        return True
    elif val.lower() == 'false':
        return False
    else:
        raise exceptions.InvalidArgument(
            message=_('值无效，必须为true或者false'))


class ServerHandler:
    class ListServerQueryStatus(TextChoices):
        EXPIRED = 'expired', _('过期')
        PREPAID = 'prepaid', _('预付费')
        POSTPAID = 'postpaid', _('后付费')

    @staticmethod
    def _list_servers_validate_params(view, request):
        service_id = request.query_params.get('service_id', None)
        ip_contain = request.query_params.get('ip-contain', None)
        public = request.query_params.get('public', None)
        remark = request.query_params.get('remark', None)
        status = request.query_params.get('status', None)
        username = request.query_params.get('username', None)
        user_id = request.query_params.get('user-id', None)
        vo_id = request.query_params.get('vo-id', None)
        vo_name = request.query_params.get('vo-name', None)
        exclude_vo = request.query_params.get('exclude-vo', None)

        if user_id is not None and username is not None:
            raise exceptions.BadRequest(
                message=_('参数“user-id”和“username”不允许同时提交')
            )

        if vo_id is not None and vo_name is not None:
            raise exceptions.BadRequest(
                message=_('参数“vo-id”和“vo-name”不允许同时提交')
            )

        if exclude_vo is not None:
            exclude_vo = True
            if vo_id is not None or vo_name is not None:
                raise exceptions.BadRequest(
                    message=_('参数"exclude-vo"不允许与参数“vo-id”和“vo-name”同时提交')
                )
        else:
            exclude_vo = False

        expired = None
        pay_type = None
        if status is not None:
            if status == ServerHandler.ListServerQueryStatus.EXPIRED.value:
                expired = True
            elif status == ServerHandler.ListServerQueryStatus.PREPAID.value:
                pay_type = PayType.PREPAID.value
            elif status == ServerHandler.ListServerQueryStatus.POSTPAID.value:
                pay_type = PayType.POSTPAID.value
            else:
                raise exceptions.InvalidArgument(message=_('参数“status”的值无效'))

        try:
            public = str_to_true_false(public)
        except exceptions.Error as e:
            raise exceptions.InvalidArgument(
                message=_('参数“public”') + str(e))

        if not view.is_as_admin_request(request):
            if username is not None:
                raise exceptions.InvalidArgument(
                    message=_('参数"username"只有以管理员身份请求时有效'))
            if user_id is not None:
                raise exceptions.InvalidArgument(
                    message=_('参数"user-id"只有以管理员身份请求时有效'))
            if vo_id is not None:
                raise exceptions.InvalidArgument(
                    message=_('参数"vo-id"只有以管理员身份请求时有效'))
            if vo_name is not None:
                raise exceptions.InvalidArgument(
                    message=_('参数"vo-name"只有以管理员身份请求时有效'))
            if exclude_vo:
                raise exceptions.InvalidArgument(
                    message=_('参数"exclude_vo"只有以管理员身份请求时有效'))

        return {
            'service_id': service_id,
            'ip_contain': ip_contain,
            'username': username,
            'user_id': user_id,
            'vo_id': vo_id,
            'vo_name': vo_name,
            'expired': expired,  # True or None
            'exclude_vo': exclude_vo,
            'public': public,
            'remark': remark,
            'pay_type': pay_type
        }

    @staticmethod
    def list_servers(view: CustomGenericViewSet, request, kwargs):
        try:
            params = ServerHandler._list_servers_validate_params(view=view, request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        service_id = params['service_id']
        ip_contain = params['ip_contain']
        username = params['username']
        user_id = params['user_id']
        vo_id = params['vo_id']
        vo_name = params['vo_name']
        expired = params['expired']
        exclude_vo = params['exclude_vo']
        public = params['public']
        remark = params['remark']
        pay_type = params['pay_type']

        if view.is_as_admin_request(request):
            try:
                servers = ServerManager().get_admin_servers_queryset(
                    user=request.user, service_id=service_id, user_id=user_id, username=username, vo_id=vo_id,
                    ipv4_contains=ip_contain, expired=expired, vo_name=vo_name, exclude_vo=exclude_vo,
                    public=public, remark=remark, pay_type=pay_type
                )
            except Exception as exc:
                return view.exception_response(exceptions.convert_to_error(exc))
        else:
            servers = ServerManager().get_user_servers_queryset(
                user=request.user, service_id=service_id, ipv4_contains=ip_contain, expired=expired,
                public=public, remark=remark, pay_type=pay_type
            )

        # service_id_map = ServiceManager.get_service_id_map(use_cache=True)
        paginator = paginations.ServersPagination()
        try:
            page = paginator.paginate_queryset(servers, request, view=view)
            serializer = serializers.ServerSerializer(page, many=True)    # context={'service_id_map': service_id_map})
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

    @staticmethod
    def list_vo_servers(view, request, kwargs):
        vo_id = kwargs.get('vo_id')
        service_id = request.query_params.get('service_id', None)
        expired = request.query_params.get('expired', None)

        if expired is not None:
            if expired.lower() == 'true':
                expired = True
            elif expired.lower() == 'false':
                expired = False
            else:
                return view.exception_response(exceptions.InvalidArgument(
                    message=_('参数“expired”值无效，必须为true或者false')))

        try:
            VoManager().get_has_read_perm_vo(vo_id=vo_id, user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        servers = ServerManager().get_vo_servers_queryset(vo_id=vo_id, service_id=service_id, expired=expired)

        # service_id_map = ServiceManager.get_service_id_map(use_cache=True)
        paginator = paginations.ServersPagination()
        try:
            page = paginator.paginate_queryset(servers, request, view=view)
            serializer = serializers.ServerSerializer(page, many=True)  # context={'service_id_map': service_id_map})
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

    @staticmethod
    def server_lock(view, request, kwargs):
        server_id = kwargs.get(view.lookup_field, '')
        lock = request.query_params.get('lock', None)
        if lock is None:
            return view.exception_response(
                exceptions.InvalidArgument(message=_('参数"lock"必须提交的')))

        if lock not in Server.Lock.values:
            return view.exception_response(
                exceptions.InvalidArgument(message=_('参数"lock"的值无效')))

        try:
            if view.is_as_admin_request(request=request):
                server = ServerManager().get_read_perm_server(
                    server_id=server_id, user=request.user, as_admin=True)
            else:
                server = ServerManager().get_read_perm_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return view.exception_response(exc)

        try:
            server.lock = lock
            server.save(update_fields=['lock'])
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data={'lock': lock})

    @staticmethod
    def server_rebuild(view, request, kwargs):
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        data = serializer.validated_data
        image_id = data.get('image_id', '')
        server_id = kwargs.get(view.lookup_field)
        try:
            server = ServerManager().get_manage_perm_server(
                server_id=server_id, user=request.user, related_fields=['vo'])
        except exceptions.Error as exc:
            return view.exception_response(exc)

        who_action = format_who_action_str(username=request.user.username)

        if server.task_status == server.TASK_CREATE_FAILED:
            return view.exception_response(
                exceptions.ConflictError(message=_('创建失败的云主机不支持重建'))
            )
        if server.task_status == server.TASK_IN_CREATING:
            return view.exception_response(
                exceptions.ConflictError(message=_('正在创建中的云主机不支持重建'))
            )

        if server.is_locked_operation():
            return view.exception_response(exceptions.ResourceLocked(
                message=_('云主机已加锁锁定了任何操作，请解锁后重试')
            ))

        service = server.service
        if service.status != service.Status.ENABLE.value:
            return view.exception_response(
                exceptions.ConflictError(message=_('提供此云服务器资源的服务单元停止服务，无法重建'))
            )

        # 过期，欠费挂起，不允许重建，需要检查是否续费，是否不再欠费
        try:
            ServerManager.check_situation_suspend(server=server)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        # 挂载云硬盘
        disk_qs = DiskManager.get_server_disks_qs(server_id=server.id)
        d_count = disk_qs.count()
        if d_count > 0:
            return view.exception_response(exceptions.DiskAttached(
                message=_('云主机挂载了%(count)s块云硬盘，请先卸载云硬盘后重试。') % {'count': d_count}
            ))

        server.task_status = server.TASK_IN_CREATING
        server.image = ''
        server.image_id = image_id
        server.image_desc = ''
        server.img_sys_type = ''
        server.img_sys_arch = ''
        server.img_release = ''
        server.img_release_version = ''
        server.default_user = ''
        server.raw_default_password = ''
        try:
            with transaction.atomic():
                server.save(update_fields=[
                    'task_status', 'image', 'image_id', 'image_desc', 'default_user', 'default_password',
                    'img_sys_type', 'img_sys_arch', 'img_release', 'img_release_version'
                ])

                params = inputs.ServerRebuildInput(instance_id=server.instance_id, instance_name=server.instance_name,
                                                   image_id=image_id, _who_action=who_action)
                try:
                    r = view.request_service(server.service, method='server_rebuild', params=params)
                except exceptions.APIException as exc:
                    raise exc

                if not r.ok:
                    raise r.error
        except Exception as exc:
            return view.exception_response(exc)

        update_fields = []
        admin_password = r.default_password
        if admin_password:
            server.raw_default_password = admin_password
            server.default_user = r.default_user if r.default_user else 'root'
            update_fields.append('default_user')
            update_fields.append('default_password')

        if r.instance_id and server.instance_id != r.instance_id:
            server.instance_id = r.instance_id
            update_fields.append('instance_id')

        if r.instance_name and server.instance_name != r.instance_name:
            server.instance_name = r.instance_name
            update_fields.append('instance_name')

        if update_fields:
            server.save(update_fields=update_fields)

        # 异步任务查询server创建结果，更新server信息和创建状态
        OrderResourceDeliverer.after_deliver_server(service=server.service, server=server)
        data = {
            'id': server.id,
            'image_id': r.image_id
        }
        return Response(data=data, status=202)

    @staticmethod
    def _server_create_validate_params(view: CustomGenericViewSet, request):
        """
        :raises: Error
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            raise exceptions.BadRequest(msg)

        data = serializer.validated_data
        image_id = data.get('image_id', '')
        flavor_id = data.get('flavor_id', '')
        network_id = data.get('network_id', '')
        remarks = data.get('remarks', '')
        pay_type = data.get('pay_type', None)
        azone_id = data.get('azone_id', None)
        vo_id = data.get('vo_id', None)
        period = data.get('period', None)
        systemdisk_size = data.get('systemdisk_size', None)
        number = data.get('number', 1)

        if not (1 <= number <= 3):
            raise exceptions.InvalidArgument(message=_('订购资源数量可选范围1-3'), code='InvalidNumber')

        if azone_id == '':
            raise exceptions.BadRequest(message=_('"azone_id"参数不能为空字符'), code='InvalidAzoneId')

        if not pay_type:
            raise exceptions.BadRequest(message=_('必须指定付费模式参数"pay_type"'), code='MissingPayType')

        pay_type_values: list = PayType.values
        pay_type_values.remove(PayType.QUOTA.value)
        if pay_type not in pay_type_values:
            raise exceptions.BadRequest(message=_('付费模式参数"pay_type"值无效'), code='InvalidPayType')

        if period is not None:
            if period <= 0:
                raise exceptions.BadRequest(message=_('订购时长参数"period"值必须大于0'), code='InvalidPeriod')

            if period > (12 * 5):
                raise exceptions.BadRequest(message=_('订购时长最长为5年'), code='InvalidPeriod')
        else:
            period = 0

        if pay_type == PayType.PREPAID.value and period == 0:
            raise exceptions.BadRequest(message=_('预付费模式时，必须指定订购时长'), code='MissingPeriod')

        flavor = Flavor.objects.filter(id=flavor_id, enable=True).first()
        if not flavor:
            raise exceptions.BadRequest(message=_('无效的配置规格flavor id'), code='InvalidFlavorId')

        if vo_id:
            try:
                vo, member = VoManager().get_has_manager_perm_vo(vo_id=vo_id, user=request.user)
            except exceptions.Error as exc:
                if exc.status_code == 404:
                    raise exceptions.BadRequest(message=str(exc), code='InvalidVoId')
                raise exc
        else:
            vo = None

        try:
            service = view.get_service(request, in_='body')
        except exceptions.NoFoundArgument:
            raise exceptions.BadRequest(message=_('参数service_id不得为空'), code='MissingServiceId')
        except exceptions.APIException as exc:
            raise exceptions.BadRequest(message=str(exc), code='InvalidServiceId')

        if not service.pay_app_service_id:
            raise exceptions.ConflictError(message=_('服务未配置对应的结算系统APP服务id'), code='ServiceNoPayAppServiceId')

        if flavor.service_id and flavor.service_id != service.id:
            raise exceptions.BadRequest(message=_('配置规格和服务单元不匹配'), code='FlavorServiceMismatch')

        try:
            out_net = view.request_service(
                service=service, method='network_detail',
                params=inputs.NetworkDetailInput(network_id=network_id, azone_id=azone_id))
        except exceptions.APIException as exc:
            if exc.status_code in [400, 404]:
                raise exceptions.BadRequest(message=_('指定网络不存在.'), code='InvalidNetworkId')

            raise exceptions.APIException(message=_('校验网络id，查询网络时错误.') + str(exc))

        network = out_net.network

        systemdisk_size = ServerHandler._validate_systemdisk_size(
            view=view, service=service, image_id=image_id, systemdisk_size=systemdisk_size
        )

        if azone_id:
            try:
                out_azones = view.request_service(
                    service=service, method='list_availability_zones',
                    params=inputs.ListAvailabilityZoneInput(region_id=service.region_id)
                )
            except exceptions.APIException as exc:
                raise exc

            azone = None
            for az in out_azones.zones:
                if az.id == azone_id:
                    azone = az
                    break

            if azone is None:
                raise exceptions.BadRequest(message=_('指定的可用区azone_id不存在'), code='InvalidAzoneId')

            azone_name = azone.name
        else:
            azone_id = azone_name = ''

        return {
            'pay_type': pay_type,
            'image_id': image_id,
            'flavor': flavor,
            'network': network,
            'azone_id': azone_id,
            'azone_name': azone_name,
            'vo': vo,
            'remarks': remarks,
            'service': service,
            'period': period,
            'systemdisk_size': systemdisk_size,
            'number': number
        }

    @staticmethod
    def _validate_systemdisk_size(view, service, image_id: str, systemdisk_size) -> int:
        """
        :raises: Error
        """
        if systemdisk_size:
            if (systemdisk_size % 50) != 0:
                raise exceptions.BadRequest(
                    message=_('系统盘大小必须是50的倍数值'), code='InvalidSystemDiskSize'
                )

        params = inputs.ImageDetailInput(image_id=image_id, region_id=service.region_id)
        try:
            r = view.request_service(service, method='image_detail', params=params)
            if not r.ok:
                raise exceptions.BadRequest(message=_('查询镜像错误') + str(r.error), code='InvalidImageId')

            min_sys_disk_gb = r.image.min_sys_disk_gb
            _adapter_client = get_service_client(service)
            min_sys_disk_gb = max(min_sys_disk_gb, _adapter_client.adapter.SYSTEM_DISK_MIN_SIZE_GB)
        except exceptions.APIException as exc:
            raise exceptions.BadRequest(message=_('查询镜像错误') + str(exc), code='InvalidImageId')

        if systemdisk_size is None:
            return min_sys_disk_gb

        if systemdisk_size < min_sys_disk_gb:
            raise exceptions.BadRequest(
                message=_('镜像要求系统盘大小不得小于%(value)dGiB') % {'value': min_sys_disk_gb},
                code='MinSystemDiskSize'
            )

        return systemdisk_size

    def server_order_create(self, view, request):
        """
        云服务器订单创建
        """
        try:
            data = ServerHandler._server_create_validate_params(view=view, request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        pay_type = data['pay_type']
        image_id = data['image_id']
        flavor = data['flavor']
        network = data['network']
        azone_id = data['azone_id']
        azone_name = data['azone_name']
        vo = data['vo']
        remarks = data['remarks']
        service = data['service']
        period = data['period']
        systemdisk_size = data['systemdisk_size']
        number = data['number']

        user = request.user
        is_public_network = network.public
        if vo or isinstance(vo, VirtualOrganization):
            vo_id = vo.id
            vo_name = vo.name
            owner_type = OwnerType.VO.value
        else:
            vo_id = ''
            vo_name = ''
            owner_type = OwnerType.USER.value

        instance_config = ServerConfig(
            vm_cpu=flavor.vcpus, vm_ram=flavor.ram_gib, systemdisk_size=systemdisk_size, public_ip=is_public_network,
            image_id=image_id, image_name='', network_id=network.id, network_name=network.name,
            azone_id=azone_id, azone_name=azone_name, flavor_id=flavor.flavor_id
        )
        omgr = OrderManager()
        # 按量付费模式时，检查是否有余额
        if pay_type == PayType.POSTPAID.value:
            # 计算按量付费一天的计费
            original_price, trade_price = omgr.calculate_amount_money(
                resource_type=ResourceType.VM.value, config=instance_config, is_prepaid=False,
                period=0, period_unit=Order.PeriodUnit.DAY.value, days=1
            )
            if number > 1:
                original_price = original_price * number

            try:
                self.__check_balance_create_server_order(
                    service=service, owner_type=owner_type, user=user, vo_id=vo_id, day_price=original_price
                )
            except Exception as exc:
                return view.exception_response(exc)

        # 服务私有资源配额是否满足需求
        try:
            QuotaAPI.service_private_quota_meet(
                service=service, vcpu=instance_config.vm_cpu * number, ram_gib=instance_config.vm_ram_gib * number,
                public_ips=number if instance_config.vm_public_ip else 0,
                private_ips=0 if instance_config.vm_public_ip else number
            )
        except exceptions.QuotaShortageError as exc:
            return view.exception_response(
                exceptions.QuotaShortageError(message=_('指定服务无法提供足够的资源。') + str(exc)))
        except exceptions.Error as exc:
            return view.exception_response(exc)

        # 创建订单
        order, resource_list = omgr.create_order(
            order_type=Order.OrderType.NEW.value,
            pay_app_service_id=service.pay_app_service_id,
            service_id=service.id,
            service_name=service.name,
            resource_type=ResourceType.VM.value,
            instance_config=instance_config,
            period=period,
            period_unit=Order.PeriodUnit.MONTH.value,
            pay_type=pay_type,
            user_id=user.id,
            username=user.username,
            vo_id=vo_id,
            vo_name=vo_name,
            owner_type=owner_type,
            remark=remarks,
            number=number
        )

        # 预付费模式时
        if pay_type == PayType.PREPAID.value:
            return Response(data={
                'order_id': order.id
            })

        try:
            subject = order.build_subject()
            order = OrderPaymentManager().pay_order(
                order=order, app_id=PAY_APP_ID, subject=subject,
                executor=request.user.username, remark='',
                coupon_ids=None, only_coupon=False,
                required_enough_balance=True
            )
            OrderResourceDeliverer().deliver_order(order=order)
        except exceptions.Error as exc:
            request_logger.error(msg=f'[{type(exc)}] {str(exc)}; Order({order.id})')

        return Response(data={
            'order_id': order.id
        })

    @staticmethod
    def __check_balance_create_server_order(service, owner_type: str, user, vo_id: str, day_price: Decimal):
        """
        按量付费模式云主机订购时，检查余额是否满足限制条件

            * 余额和券金额 / 按量一天计费金额 = 服务单元可以创建的按量付费云主机数量

        :raises: Error, BalanceNotEnough
        """
        lower_limit_amount = Decimal('100.00')
        if owner_type == OwnerType.USER.value:
            qs = ServerManager().get_user_servers_queryset(
                user=user, service_id=service.id, pay_type=PayType.POSTPAID.value)
            s_count = qs.count()
            money_amount = day_price * s_count + lower_limit_amount

            if not PaymentManager().has_enough_balance_user(
                    user_id=user.id, money_amount=money_amount, with_coupons=True,
                    app_service_id=service.pay_app_service_id
            ):
                raise exceptions.BalanceNotEnough(
                    message=_('你在指定服务单元中已拥有%(value)d台按量计费的云主机，你的余额不足，不能订购更多的云主机。'
                              ) % {'value': s_count})
        else:
            qs = ServerManager().get_vo_servers_queryset(
                vo_id=vo_id, service_id=service.id, pay_type=PayType.POSTPAID.value)
            s_count = qs.count()
            money_amount = day_price * s_count + lower_limit_amount

            if not PaymentManager().has_enough_balance_vo(
                    vo_id=vo_id, money_amount=money_amount, with_coupons=True,
                    app_service_id=service.pay_app_service_id
            ):
                raise exceptions.BalanceNotEnough(
                    message=_('项目组在指定服务单元中已拥有%(value)d台按量计费的云主机，项目组的余额不足，不能订购更多的云主机。'
                              ) % {'value': s_count}, code='VoBalanceNotEnough')

    @staticmethod
    def renew_server(view, request, kwargs):
        """
        续费云服务器
        """
        try:
            data = ServerHandler._renew_server_validate_params(request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        period = data['period']
        renew_to_time = data['renew_to_time']

        server_id = kwargs.get(view.lookup_field, '')

        try:
            server = ServerManager().get_manage_perm_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return view.exception_response(exc)

        if server.expiration_time is None:
            return view.exception_response(exceptions.UnknownExpirationTime(message=_('没有过期时间的云服务器无法续费。')))

        if renew_to_time:
            if server.expiration_time >= renew_to_time:
                return view.exception_response(exceptions.ConflictError(
                    message=_('指定的续费终止日期必须在云服务器的过期时间之后。'), code='InvalidRenewToTime'))

        if server.is_locked_operation():
            return view.exception_response(exceptions.ResourceLocked(
                message=_('云主机已加锁锁定了一切操作')
            ))

        if server.pay_type != PayType.PREPAID.value:
            return view.exception_response(exceptions.RenewPrepostOnly(message=_('只允许包年包月按量计费的云服务器续费。')))

        if server.task_status != server.TASK_CREATED_OK:
            return view.exception_response(exceptions.RenewDeliveredOkOnly(message=_('只允许为创建成功的云服务器续费。')))

        try:
            service = ServiceManager.get_service(server.service_id)
            if not service.pay_app_service_id:
                raise exceptions.ConflictError(
                    message=_('云主机服务未配置对应的结算系统APP服务id'), code='ServiceNoPayAppServiceId')
        except exceptions.Error as exc:
            return view.exception_response(exc)

        if service.status != service.Status.ENABLE.value:
            return view.exception_response(
                exceptions.ConflictError(message=_('提供此云服务器资源的服务单元停止服务，不允许续费'))
            )

        network_id = server.network_id
        network_name = ''
        if network_id:
            try:
                out_net = view.request_service(
                    service=service, method='network_detail', params=inputs.NetworkDetailInput(network_id=network_id))
                network_name = out_net.network.name
            except Exception as exc:
                pass

        if not network_name:
            network_name = server.ipv4

        _order = Order.objects.filter(
            resource_type=ResourceType.VM.value, resource_set__instance_id=server.id,
            trading_status__in=[Order.TradingStatus.OPENING.value, Order.TradingStatus.UNDELIVERED.value]
        ).order_by('-creation_time').first()
        if _order is not None:
            return view.exception_response(exceptions.SomeOrderNeetToTrade(
                message=_('此云服务器存在未完成的订单（%s）, 请先完成已有订单后再提交新的订单。') % _order.id))

        with transaction.atomic():
            server = ServerManager.get_server_queryset().select_related(
                'service', 'user', 'vo').select_for_update().get(id=server_id)

            start_time = None
            end_time = None
            if renew_to_time:
                start_time = server.expiration_time
                end_time = renew_to_time
                period = 0

            if server.belong_to_vo():
                owner_type = OwnerType.VO.value
                vo_id = server.vo_id
                vo_name = server.vo.name
            else:
                owner_type = OwnerType.USER.value
                vo_id = ''
                vo_name = ''

            instance_config = ServerConfig(
                vm_cpu=server.vcpus, vm_ram=server.ram_gib,
                systemdisk_size=server.disk_size, public_ip=server.public_ip,
                image_id=server.image_id, image_name=server.image, network_id=network_id, network_name=network_name,
                azone_id=server.azone_id, azone_name='', flavor_id=''
            )
            order, resource = OrderManager().create_renew_order(
                pay_app_service_id=service.pay_app_service_id,
                service_id=server.service_id,
                service_name=server.service.name,
                resource_type=ResourceType.VM.value,
                instance_id=server.id,
                instance_config=instance_config,
                period=period,
                start_time=start_time,
                end_time=end_time,
                user_id=request.user.id,
                username=request.user.username,
                vo_id=vo_id,
                vo_name=vo_name,
                owner_type=owner_type
            )

        return Response(data={'order_id': order.id})

    @staticmethod
    def _renew_server_validate_params(request):
        period = request.query_params.get('period', None)
        renew_to_time = request.query_params.get('renew_to_time', None)
        if period is not None and renew_to_time is not None:
            raise exceptions.BadRequest(message=_('参数“period”和“renew_to_time”不能同时提交'))

        if period is None and renew_to_time is None:
            raise exceptions.BadRequest(message=_('参数“period”不得为空'), code='MissingPeriod')

        if period is not None:
            try:
                period = int(period)
                if period <= 0:
                    raise ValueError
            except ValueError:
                raise exceptions.InvalidArgument(message=_('参数“period”的值无效'), code='InvalidPeriod')

        if renew_to_time is not None:
            renew_to_time = iso_utc_to_datetime(renew_to_time)
            if not isinstance(renew_to_time, datetime):
                raise exceptions.InvalidArgument(
                    message=_('参数“renew_to_time”的值无效的时间格式'), code='InvalidRenewToTime')

        return {
            'period': period,
            'renew_to_time': renew_to_time
        }

    @staticmethod
    def server_suspend(view, request, kwargs):
        """云服务器过期、欠费停机挂起"""
        server_id = kwargs.get(view.lookup_field, '')
        act = request.query_params.get('act', None)
        if act is None:
            return view.exception_response(
                exceptions.InvalidArgument(message=_('参数"act"必须提交')))

        if act not in Server.Situation.values:
            return view.exception_response(
                exceptions.InvalidArgument(message=_('参数"act"的值无效')))

        try:
            server = ServerManager().get_read_perm_server(
                server_id=server_id, user=request.user, as_admin=True)
        except exceptions.APIException as exc:
            return view.exception_response(exc)

        try:
            ServerManager.do_suspend_server(server=server, situation=act)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data={'act': act})

    def delete_server(self, view: CustomGenericViewSet, request, kwargs):
        server_id = kwargs.get(view.lookup_field, '')
        q_force = request.query_params.get('force', '')
        if q_force.lower() == 'true':
            force = True
        else:
            force = False

        try:
            self._do_delete_server(
                server_id=server_id, force=force, user=request.user,
                is_as_admin=view.is_as_admin_request(request=request)
            )
        except exceptions.APIException as exc:
            return view.exception_response(exc)

        return Response(status=204)

    @staticmethod
    def _do_delete_server(server_id: str, force: bool, user, is_as_admin: bool):
        """
        :return:
            True        # delete ok
            raise Error # delete failed
        """
        if is_as_admin:
            server = ServerManager().get_manage_perm_server(
                server_id=server_id, user=user, related_fields=['service__org_data_center'], as_admin=True)
        else:
            server = ServerManager().get_manage_perm_server(
                server_id=server_id, user=user, related_fields=['service__org_data_center', 'vo__owner'])

        if server.is_locked_delete():
            raise exceptions.ResourceLocked(message=_('无法删除，云主机已加锁锁定了删除'))

        who_action = format_who_action_str(username=user.username)
        # 卸载云硬盘
        disks = DiskManager.get_server_disks_qs(server_id=server.id)
        for disk in disks:
            DiskHandler.do_detach_disk(server=disk.server, disk=disk, user=user)

        try:
            params = inputs.ServerDeleteInput(
                instance_id=server.instance_id, instance_name=server.instance_name, force=force, _who_action=who_action)
            core_request.request_service(server.service, method='server_delete', params=params)
        except exceptions.APIException as exc:
            raise exc

        server_id = server.id
        if server.do_archive(archive_user=user):  # 记录归档
            ServerHandler.release_server_quota(server=server)  # 释放资源配额

        server.id = server_id
        ResourceActionLogManager.add_delete_log_for_resource(res=server, user=user, raise_error=False)
        OrderManager.set_resource_server_deleted(instance_id=server_id, raise_exc=False)
        return True

    @staticmethod
    def release_server_quota(server):
        """
        释放虚拟服务器资源配额

        :param server: 服务器对象
        :return:
            True
            False
        """
        if server.public_ip:
            public_ips = 1
            private_ips = 0
        else:
            public_ips = 0
            private_ips = 1

        try:
            QuotaAPI().server_quota_release(
                service=server.service, vcpu=server.vcpus, ram_gib=server.ram_gib,
                public_ips=public_ips, private_ips=private_ips)
        except exceptions.Error as e:
            return False

        return True

    def server_action(self, view: CustomGenericViewSet, request, kwargs):
        server_id = kwargs.get(view.lookup_field, '')
        try:
            act = request.data.get('action', None)
        except Exception as e:
            exc = exceptions.InvalidArgument(_('参数有误') + ',' + str(e))
            return Response(data=exc.err_data(), status=exc.status_code)

        actions = inputs.ServerAction.values  # ['start', 'reboot', 'shutdown', 'poweroff', 'delete', 'delete_force']
        if act is None:
            exc = exceptions.InvalidArgument(_('action参数是必须的'))
            return Response(data=exc.err_data(), status=exc.status_code)

        if act not in actions:
            exc = exceptions.InvalidArgument(_('action参数无效'))
            return Response(data=exc.err_data(), status=exc.status_code)

        is_as_admin = view.is_as_admin_request(request=request)
        try:
            if act in [inputs.ServerAction.DELETE, inputs.ServerAction.DELETE_FORCE]:
                self._do_delete_server(
                    server_id=server_id, user=request.user, force=bool(act == inputs.ServerAction.DELETE_FORCE),
                    is_as_admin=is_as_admin
                )
            else:
                self._do_server_normal_action(
                    server_id=server_id, act=act, user=request.user, is_as_admin=is_as_admin
                )
        except exceptions.APIException as exc:
            return view.exception_response(exc)

        return Response({'action': act})

    @staticmethod
    def _do_server_normal_action(server_id: str, act: str, user, is_as_admin: bool):
        """
        :raises: APIException
        """
        if is_as_admin:
            server = ServerManager().get_read_perm_server(
                server_id=server_id, user=user, related_fields=['service__org_data_center'], as_admin=True)
        else:
            server = ServerManager().get_read_perm_server(
                server_id=server_id, user=user, related_fields=['service__org_data_center', 'vo__owner'])

        if server.is_locked_operation():
            raise exceptions.ResourceLocked(message=_('云主机已加锁锁定了任何操作'))

        # 过期，欠费挂起，不允许开机，需要检查是否续费，是否不再欠费
        if act in [inputs.ServerAction.START, inputs.ServerAction.REBOOT]:
            ServerManager.check_situation_suspend(server=server)
            ServerManager.not_allow_start_server_check(server=server)

        who_action = format_who_action_str(username=user.username)
        try:
            params = inputs.ServerActionInput(
                instance_id=server.instance_id, instance_name=server.instance_name, action=act, _who_action=who_action)
            r = core_request.request_service(server.service, method='server_action', params=params)
        except exceptions.APIException as exc:
            raise exc

        return True

    @staticmethod
    def modify_server_pay_type(view: CustomGenericViewSet, request, kwargs):
        """
        修改云服务器计费方式
        """
        try:
            data = ServerHandler._modify_pay_type_validate_params(request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        period = data['period']
        new_pay_type = data['pay_type']
        server_id = kwargs.get(view.lookup_field, '')

        try:
            server = ServerManager().get_manage_perm_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return view.exception_response(exc)

        if server.is_locked_operation():
            return view.exception_response(exceptions.ResourceLocked(
                message=_('云主机已加锁锁定了一切操作')
            ))

        if server.task_status != server.TASK_CREATED_OK:
            return view.exception_response(
                exceptions.ConflictError(message=_('只允许为创建成功的云服务器修改计费方式。')))

        try:
            service = ServiceManager.get_service(server.service_id)
            if not service.pay_app_service_id:
                raise exceptions.ConflictError(
                    message=_('云服务器所在服务单元未配置对应的结算系统APP服务id'), code='ServiceNoPayAppServiceId')
        except exceptions.Error as exc:
            return view.exception_response(exc)

        if service.status != service.Status.ENABLE.value:
            return view.exception_response(
                exceptions.ConflictError(message=_('提供此云服务器资源的服务单元停止服务，不允许修改计费方式。'))
            )

        if new_pay_type == PayType.PREPAID.value:
            if server.pay_type != PayType.POSTPAID.value:
                return view.exception_response(
                    exceptions.ConflictError(message=_('必须是按量计费方式的服务器实例才可以转为包年包月计费方式。')))

        _order = Order.objects.filter(
            resource_type=ResourceType.VM.value, resource_set__instance_id=server.id,
            trading_status__in=[Order.TradingStatus.OPENING.value, Order.TradingStatus.UNDELIVERED.value]
        ).order_by('-creation_time').first()
        if _order is not None:
            return view.exception_response(exceptions.SomeOrderNeetToTrade(
                message=_('此云服务器存在未完成的订单（%s）, 请先完成已有订单后再提交新的订单。') % _order.id))

        with transaction.atomic():
            server = ServerManager.get_server_queryset().select_related(
                'service', 'user', 'vo').select_for_update().get(id=server_id)

            if server.belong_to_vo():
                owner_type = OwnerType.VO.value
                vo_id = server.vo_id
                vo_name = server.vo.name
            else:
                owner_type = OwnerType.USER.value
                vo_id = ''
                vo_name = ''

            instance_config = ServerConfig(
                vm_cpu=server.vcpus, vm_ram=server.ram_gib,
                systemdisk_size=server.disk_size, public_ip=server.public_ip,
                image_id=server.image_id, image_name=server.image,
                network_id=server.network_id, network_name='',
                azone_id=server.azone_id, azone_name='', flavor_id=''
            )
            order, resource = OrderManager().create_change_pay_type_order(
                pay_type=new_pay_type,
                pay_app_service_id=service.pay_app_service_id,
                service_id=server.service_id,
                service_name=server.service.name,
                resource_type=ResourceType.VM.value,
                instance_id=server.id,
                instance_config=instance_config,
                period=period,
                user_id=request.user.id,
                username=request.user.username,
                vo_id=vo_id,
                vo_name=vo_name,
                owner_type=owner_type
            )

        return Response(data={'order_id': order.id})

    @staticmethod
    def _modify_pay_type_validate_params(request):
        period = request.query_params.get('period', None)
        pay_type = request.query_params.get('pay_type', None)

        if pay_type is None:
            raise exceptions.BadRequest(message=_('必须指定付费方式'), code='MissingPayType')

        if pay_type not in [PayType.PREPAID.value]:
            raise exceptions.InvalidArgument(message=_('指定付费方式无效'), code='InvalidPayType')

        if pay_type == PayType.PREPAID.value:
            if period is None:
                raise exceptions.BadRequest(message=_('按量计费转包年包月必须指定续费时长'), code='MissingPeriod')

            try:
                period = int(period)
                if period <= 0:
                    raise ValueError
            except ValueError:
                raise exceptions.InvalidArgument(message=_('指定续费时长无效'), code='InvalidPeriod')

        return {
            'period': period,
            'pay_type': pay_type
        }


class ServerArchiveHandler:
    @staticmethod
    def list_archives(view, request, kwargs):
        service_id = request.query_params.get('service_id', None)
        queryset = ServerArchiveManager().get_user_archives_queryset(
            user=request.user, service_id=service_id)

        paginator = view.paginator
        try:
            page = paginator.paginate_queryset(queryset, request=request, view=view)
            serializer = serializers.ServerArchiveSerializer(page, many=True)
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

    @staticmethod
    def list_vo_archives(view, request, kwargs):
        vo_id = kwargs.get('vo_id')
        service_id = request.query_params.get('service_id', None)

        vo_mgr = VoManager()
        vo = vo_mgr.get_vo_by_id(vo_id)
        if vo is None:
            raise exceptions.NotFound(message=_('项目组不存在'))

        try:
            vo_mgr.check_read_perm(vo=vo, user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        queryset = ServerArchiveManager().get_vo_archives_queryset(vo_id=vo_id, service_id=service_id)
        paginator = view.paginator
        try:
            page = paginator.paginate_queryset(queryset, request, view=view)
            serializer = serializers.ServerArchiveSerializer(page, many=True)
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))
