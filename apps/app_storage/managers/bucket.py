from django.utils.translation import gettext as _
from django.utils import timezone

from core import errors
from apps.app_storage.models import Bucket, ObjectsService
from apps.app_storage.managers.objects_service import ObjectsServiceManager


class BucketManager:
    @staticmethod
    def get_bucket_queryset():
        return Bucket.objects.all()

    @staticmethod
    def get_bucket_by_id(_id: str):
        """
        :return: None or ObjectsService()
        """
        return Bucket.objects.filter(id=_id).first()

    @staticmethod
    def get_bucket(service_id: str, bucket_name: str):
        """
        :raises: BucketNotExist
        """
        bucket = Bucket.objects.select_related('service').filter(service_id=service_id, name=bucket_name).first()
        if not bucket:
            raise errors.BucketNotExist(_('存储桶不存在'))

        return bucket

    @staticmethod
    def get_user_bucket(service_id: str, bucket_name: str, user):
        """
        :raises: BucketNotExist, BucketNotOwned
        """
        bucket = BucketManager.get_bucket(service_id=service_id, bucket_name=bucket_name)
        if bucket.user_id != user.id:
            raise errors.BucketNotOwned(message=_('你无权访问此存储桶'))

        return bucket

    @staticmethod
    def get_user_service_bucket_count(service_id: str, user):
        """
        用户在指定服务单元桶的数量
        """
        return Bucket.objects.filter(user_id=user.id, service_id=service_id).count()

    @staticmethod
    def create_bucket(bucket_name, bucket_id: str, user_id: str, service_id: str,
                      task_status=Bucket.TaskStatus.SUCCESS.value) -> Bucket:
        """
        :param bucket_name: 桶名称
        :param bucket_id: 对象存储服务单元中bucket id
        :param user_id: 桶拥有者id
        :param service_id: 桶所在服务单元id
        :param task_status: 桶创建状态
        """
        bucket = Bucket(
            name=bucket_name, bucket_id=bucket_id, user_id=user_id, task_status=task_status,
            service_id=service_id, creation_time=timezone.now()
        )
        bucket.save(force_insert=True)
        return bucket

    def filter_bucket_queryset(self, user_id: str, service_id: str = None):
        queryset = self.get_bucket_queryset()
        queryset = queryset.select_related('service', 'user')
        queryset = queryset.filter(user_id=user_id)

        if service_id:
            queryset = queryset.filter(service_id=service_id)

        return queryset

    def admin_filter_bucket_queryset(self, admin_user, service_id: str = None, user_id: str = None):
        queryset = self.get_bucket_queryset()
        queryset = queryset.select_related('service', 'user')

        if not admin_user.is_federal_admin():
            if service_id:
                s = ObjectsServiceManager.get_service_if_admin(user=admin_user, service_id=service_id)
                if s is None:
                    raise errors.AccessDenied(message=_('你没有指定服务单元的管理权限。'))
            else:
                service_ids = ObjectsServiceManager.get_has_perm_service_ids(user_id=admin_user.id)
                queryset = queryset.filter(service_id__in=service_ids)

        if service_id:
            queryset = queryset.filter(service_id=service_id)

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset
