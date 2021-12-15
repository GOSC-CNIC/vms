from uuid import uuid1

from django.db import models
from django.db.models import Count, Sum, Q
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils import timezone

from service.models import ServiceConfig, UserQuota
from utils.model import get_encryptor
from vo.models import VirtualOrganization

User = get_user_model()


def get_uuid1_str():
    return str(uuid1())


class ServerBase(models.Model):
    """
    虚拟服务器实例
    """
    TASK_CREATED_OK = 1
    TASK_IN_CREATING = 2
    TASK_CREATE_FAILED = 3
    CHOICES_TASK = (
        (TASK_CREATED_OK, _('创建成功')),
        (TASK_IN_CREATING, _('正在创建中')),
        (TASK_CREATE_FAILED, _('创建失败')),
    )

    QUOTA_PRIVATE = 1
    QUOTA_SHARED = 2
    CHOICES_QUOTA = (
        (QUOTA_PRIVATE, _('私有资源配额')),
        (QUOTA_SHARED, _('共享资源配额'))
    )

    class Classification(models.TextChoices):
        PERSONAL = 'personal', _('个人的')
        VO = 'vo', _('VO组的')

    id = models.CharField(blank=True, editable=False, max_length=36, primary_key=True, verbose_name='ID')
    name = models.CharField(max_length=255, verbose_name=_('服务器实例名称'))
    instance_id = models.CharField(max_length=128, verbose_name=_('虚拟主机ID'), help_text=_('各接入服务中虚拟主机的ID'))
    instance_name = models.CharField(max_length=255, default='', verbose_name=_('云主机名称'),
                                     help_text=_('各接入服务中虚拟主机的名称'))
    vcpus = models.IntegerField(verbose_name=_('虚拟CPU数'), default=0)
    ram = models.IntegerField(verbose_name=_('内存MB'), default=0)
    ipv4 = models.CharField(max_length=128, verbose_name='IPV4', default='')
    public_ip = models.BooleanField(default=True, verbose_name=_('公/私网'))
    image = models.CharField(max_length=255, verbose_name=_('镜像系统名称'), default='')
    image_id = models.CharField(max_length=64, verbose_name=_('镜像系统ID'), default='')
    image_desc = models.CharField(max_length=255, verbose_name=_('镜像系统描述'), blank=True, default='')
    default_user = models.CharField(max_length=64, verbose_name=_('默认登录用户名'), default='')
    default_password = models.CharField(max_length=255, blank=True, verbose_name=_('默认登录密码'), default='')
    creation_time = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))
    remarks = models.CharField(max_length=255, blank=True, default='', verbose_name=_('备注'))
    task_status = models.SmallIntegerField(verbose_name=_('创建状态'), choices=CHOICES_TASK, default=TASK_CREATED_OK)
    center_quota = models.SmallIntegerField(verbose_name=_('服务配额'), choices=CHOICES_QUOTA, default=QUOTA_PRIVATE)
    expiration_time = models.DateTimeField(verbose_name=_('过期时间'), null=True, blank=True, default=None)
    classification = models.CharField(verbose_name=_('云主机归属类型'), max_length=16,
                                      choices=Classification.choices, default=Classification.PERSONAL,
                                      help_text=_('标识云主机属于申请者个人的，还是vo组的'))

    class Meta:
        abstract = True

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            self.id = get_uuid1_str()

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    def do_delete(self):
        """
        :return: True or False
        """
        try:
            self.delete()
        except Exception as e:
            return False

        return True

    @property
    def is_use_shared_quota(self):
        """是否使用的数据中心共享资源配额"""
        return self.center_quota == self.QUOTA_SHARED

    @property
    def is_use_private_quota(self):
        """是否使用的数据中心私有资源配额"""
        return self.center_quota == self.QUOTA_PRIVATE

    @staticmethod
    def count_user_quota_used(user_quota):
        """
        用户资源配额已用统计

        :param user_quota: 用户配额
        :return:
            {
                'vcpu_used_count': 1,
                'ram_used_count': 80,
                'public_ip_count': 0,
                'private_ip_count': 1
            }
        """
        stat = Server.objects.filter(user_quota=user_quota).aggregate(
            vcpu_used_count=Sum('vcpus'), ram_used_count=Sum('ram'),
            public_ip_count=Count('id', filter=Q(public_ip=True)),
            private_ip_count=Count('id', filter=Q(public_ip=False))
        )
        if stat.get('vcpu_used_count', 0) is None:
            stat['vcpu_used_count'] = 0

        if stat.get('ram_used_count', 0) is None:
            stat['ram_used_count'] = 0

        return stat

    @property
    def raw_default_password(self):
        """
        :return:
            str     # success
            None    # failed, invalid encrypted password
        """
        encryptor = get_encryptor()
        try:
            return encryptor.decrypt(self.default_password)
        except encryptor.InvalidEncrypted as e:
            return None

    @raw_default_password.setter
    def raw_default_password(self, raw_password: str):
        encryptor = get_encryptor()
        self.default_password = encryptor.encrypt(raw_password)

    def belong_to_vo(self):
        return self.classification == self.Classification.VO


class Server(ServerBase):
    """
    虚拟服务器实例
    """
    class Lock(models.TextChoices):
        FREE = 'free', _('无锁')
        DELETE = 'lock-delete', _('锁定删除')
        OPERATION = 'lock-operation', _('锁定所有操作，只允许读')

    service = models.ForeignKey(to=ServiceConfig, null=True, on_delete=models.SET_NULL, related_name='server_set',
                                verbose_name=_('接入的服务配置'))
    user = models.ForeignKey(to=User, verbose_name=_('创建者'), on_delete=models.SET_NULL, related_name='user_servers',
                             null=True)
    user_quota = models.ForeignKey(to=UserQuota, blank=True, null=True, on_delete=models.SET_NULL,
                                   related_name='quota_servers', verbose_name=_('所属用户配额'))
    vo = models.ForeignKey(to=VirtualOrganization, null=True, on_delete=models.SET_NULL, default=None, blank=True,
                           related_name='vo_server_set', verbose_name=_('项目组'))
    lock = models.CharField(verbose_name=_('锁'), max_length=16, choices=Lock.choices, default=Lock.FREE,
                            help_text=_('加锁锁定云主机，防止误操作'))
    # email_lasttime = models.DateTimeField(verbose_name=_('上次发送邮件时间'), null=True, default=None,
    #                                       help_text=_('记录上次发邮件的时间，邮件通知用户配额即将到期'))

    class Meta:
        ordering = ['-creation_time']
        verbose_name = _('虚拟服务器')
        verbose_name_plural = verbose_name

    def user_has_perms(self, user):
        """
        用户是否有访问此宿主机的权限

        :param user: 用户
        :return:
            True    # has
            False   # no
        """
        if not user.id:    # 未认证用户
            return False

        if user.is_superuser:
            return True

        if self.user_id == user.id:
            return True

        return False

    def do_archive(self):
        """
        创建归档记录
        :return: True or False
        """
        if not self.id:
            return False

        a = ServerArchive()
        try:
            a.service = self.service
            a.name = self.name
            a.instance_id = self.instance_id
            a.instance_name = self.instance_name
            a.vcpus = self.vcpus
            a.ram = self.ram
            a.ipv4 = self.ipv4
            a.public_ip = self.public_ip
            a.image = self.image
            a.creation_time = self.creation_time
            a.remarks = self.remarks
            a.user_id = self.user_id
            a.vo_id = self.vo_id
            a.deleted_time = timezone.now()
            a.task_status = self.task_status
            a.center_quota = self.center_quota
            a.user_quota = self.user_quota
            a.expiration_time = self.expiration_time
            a.classification = self.classification
            a.image_id = self.image_id
            a.image_desc = self.image_desc
            a.default_user = self.default_user
            a.default_password = self.default_password
            a.save()
        except Exception as e:
            return False

        if not self.do_delete():
            a.do_delete()

        return True

    @staticmethod
    def count_private_quota_used(service):
        """
        接入服务的私有资源配额已用统计

        :param service: 接入服务配置对象
        :return:
            {
                'vcpu_used_count': 1,
                'ram_used_count': 80,
                'public_ip_count': 0,
                'private_ip_count': 1
            }
        """
        if not isinstance(service, models.Model):
            service_id = service
        else:
            service_id = service.id

        stat = Server.objects.filter(service=service_id, center_quota=Server.QUOTA_PRIVATE).aggregate(
            vcpu_used_count=Sum('vcpus'), ram_used_count=Sum('ram'),
            public_ip_count=Count('id', filter=Q(public_ip=True)),
            private_ip_count=Count('id', filter=Q(public_ip=False))
        )
        if stat.get('vcpu_used_count', 0) is None:
            stat['vcpu_used_count'] = 0

        if stat.get('ram_used_count', 0) is None:
            stat['ram_used_count'] = 0

        return stat

    @staticmethod
    def count_share_quota_used(service):
        """
        接入服务的分享资源配额已用统计

        :param service: 接入服务配置对象
        :return:
            {
                'vcpu_used_count': 1,
                'ram_used_count': 80,
                'public_ip_count': 0,
                'private_ip_count': 1
            }
        """
        if not isinstance(service, models.Model):
            service_id = service
        else:
            service_id = service.id

        stat = Server.objects.filter(service=service_id, center_quota=Server.QUOTA_SHARED).aggregate(
            vcpu_used_count=Sum('vcpus'), ram_used_count=Sum('ram'),
            public_ip_count=Count('id', filter=Q(public_ip=True)),
            private_ip_count=Count('id', filter=Q(public_ip=False))
        )
        if stat.get('vcpu_used_count', 0) is None:
            stat['vcpu_used_count'] = 0

        if stat.get('ram_used_count', 0) is None:
            stat['ram_used_count'] = 0

        return stat

    def is_locked_operation(self):
        """
        是否加锁, 锁定了一切操作
        :return:
            True        # locked
            False       # not locked
        """
        return self.lock == self.Lock.OPERATION

    def is_locked_delete(self):
        """
        检查是否加锁，是否锁定删除
        :return:
            True        # lock delete
            False       # not lock delete
        """
        return self.lock in [self.Lock.DELETE, self.Lock.OPERATION]


class ServerArchive(ServerBase):
    """
    虚拟服务器实例归档
    """
    service = models.ForeignKey(to=ServiceConfig, null=True, on_delete=models.SET_NULL,
                                related_name='server_archive_set', verbose_name=_('接入的服务配置'))
    user = models.ForeignKey(to=User, verbose_name=_('创建者'), on_delete=models.SET_NULL,
                             related_name='user_server_archives', null=True)
    user_quota = models.ForeignKey(to=UserQuota, null=True, on_delete=models.SET_NULL,
                                   related_name='server_archive_set', verbose_name=_('所属用户配额'))
    vo = models.ForeignKey(to=VirtualOrganization, null=True, on_delete=models.SET_NULL, default=None, blank=True,
                           related_name='vo_server_archive_set', verbose_name=_('项目组'))
    deleted_time = models.DateTimeField(verbose_name=_('删除归档时间'), auto_now_add=True)

    class Meta:
        ordering = ['-deleted_time']
        verbose_name = _('服务器归档记录')
        verbose_name_plural = verbose_name


class Flavor(models.Model):
    id = models.CharField(blank=True, editable=False, max_length=36, primary_key=True, verbose_name='ID')
    vcpus = models.IntegerField(verbose_name=_('虚拟CPU数'), default=0)
    ram = models.IntegerField(verbose_name=_('内存MB'), default=0)
    enable = models.BooleanField(verbose_name=_('可用状态'), default=True)
    creation_time = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))

    class Meta:
        db_table = 'flavor'
        ordering = ['vcpus']
        verbose_name = _('配置样式')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'Flavor(vcpus={self.vcpus}, ram={self.ram}Mb)'

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            self.id = get_uuid1_str()

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)
