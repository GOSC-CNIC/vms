from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.functional import cached_property

from utils.model import UuidModel
from apps.app_users.models import UserProfile
from apps.app_net_manage.models import OrgVirtualObject


class NetLinkUserRole(UuidModel):
    """用户角色和权限"""
    user = models.OneToOneField(
        verbose_name=_('用户'), to=UserProfile, related_name='+', on_delete=models.CASCADE)
    is_link_admin = models.BooleanField(
        verbose_name=_('链路管理员'), default=False, help_text=_('选中，用户拥有链路管理功能的管理员权限'))
    is_link_readonly = models.BooleanField(
        verbose_name=_('链路管理全局只读权限'), default=False, help_text=_('选中，用户拥有链路管理功能的全局只读权限'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    update_time = models.DateTimeField(verbose_name=_('更新时间'))

    class Meta:
        ordering = ('-creation_time',)
        db_table = 'net_link_user_role'
        verbose_name = _('01_网络链路管理用户角色和权限')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.user.username


class FiberCable(UuidModel):
    """光缆"""

    number = models.CharField(verbose_name=_('光缆编号'), max_length=64, default='')
    fiber_count = models.IntegerField(verbose_name=_('总纤芯数量'))
    length = models.DecimalField(
        verbose_name=_('长度'), max_digits=10, decimal_places=2, null=True, blank=True, default=None, help_text='km')
    endpoint_1 = models.CharField(verbose_name=_('端点1'), max_length=255, blank=True, default='')
    endpoint_2 = models.CharField(verbose_name=_('端点2'), max_length=255, blank=True, default='')
    remarks = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        ordering = ('-update_time',)
        db_table = 'net_link_fiber_cable'
        verbose_name = _('光缆')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.number


class DistributionFrame(UuidModel):
    """配线架"""

    number = models.CharField(verbose_name=_('设备号'), max_length=64, default='')
    model_type = models.CharField(verbose_name=_('设备型号'), max_length=36, blank=True, default='')
    row_count = models.IntegerField(verbose_name=_('行数'), default=0)
    col_count = models.IntegerField(verbose_name=_('列数'), default=0)
    place = models.CharField(verbose_name=_('位置'), max_length=128, blank=True, default='')
    link_org = models.ForeignKey(
        verbose_name=_('机构二级'), to=OrgVirtualObject, related_name='+',
        on_delete=models.SET_NULL, null=True, default=None)
    remarks = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        ordering = ('-update_time',)
        db_table = 'net_link_distribution_frame'
        verbose_name = _('配线架')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.number


class Element(UuidModel):
    """网元汇总表"""

    class Type(models.TextChoices):
        """数据库网元类型"""
        OPTICAL_FIBER = 'fiber', _('光纤')
        LEASE_LINE = 'lease', _('租用线路')
        DISTRIFRAME_PORT = 'port', _('配线架端口')
        CONNECTOR_BOX = 'box', _('光缆接头盒')

    object_type = models.CharField(verbose_name=_('网元对象类型'), max_length=32, choices=Type.choices)
    object_id = models.CharField(verbose_name=_('网元对象id'), max_length=36, db_index=True)
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        ordering = ('-create_time',)
        db_table = 'net_link_element'
        verbose_name = _('网元汇总表')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.object_type}:{self.object_id}'

    def is_repetable_creat_link(self):
        """该网元是否可重复建立链路"""
        if self.object_type == Element.Type.CONNECTOR_BOX:
            return True

        return False

    def is_linkable(self):
        """该网元能否建立链路"""
        return self.is_repetable_creat_link() or not self.is_linked()

    def is_linked(self):
        """该网元是否已经建立链路"""
        return bool(self.related_link_ids)

    @cached_property
    def related_link_ids(self):
        return self.links.all().values_list('id', flat=True)


class ElementBase(UuidModel):
    """网元对象基类"""

    element = models.OneToOneField(
        verbose_name=_('网元记录'), to=Element, related_name='element_%(class)s',
        db_constraint=False, on_delete=models.SET_NULL, null=True, default=None)

    class Meta:
        abstract = True

    @property
    def is_linked(self):
        if self.element is None:
            return False

        return self.element.is_linked()

    @property
    def link_id(self):
        if not self.is_linked:
            return []

        return self.element.related_link_ids


class LeaseLine(ElementBase):
    """租用线路"""

    class LeaseStatus(models.TextChoices):
        """租线状态"""
        ENABLE = 'enable', _('在网')
        DISABLE = 'disable', _('撤线')

    private_line_number = models.CharField(verbose_name=_('专线号'), max_length=64, blank=True, default='')
    lease_line_code = models.CharField(verbose_name=_('电路代号'), max_length=64, blank=True, default='')
    line_username = models.CharField(verbose_name=_('专线用户'), max_length=36, blank=True, default='')
    endpoint_a = models.CharField(verbose_name=_('A端'), max_length=255, blank=True, default='')
    endpoint_z = models.CharField(verbose_name=_('Z端'), max_length=255, blank=True, default='')
    line_type = models.CharField(verbose_name=_('线路类型'), max_length=36, blank=True, default='')
    cable_type = models.CharField(verbose_name=_('电路类型'), max_length=36, blank=True, default='')
    bandwidth = models.IntegerField(verbose_name=_('带宽'), null=True, blank=True, default=None, help_text='Mbps')
    length = models.DecimalField(
        verbose_name=_('长度'), max_digits=10, decimal_places=2, null=True, blank=True, default=None, help_text='km')
    provider = models.CharField(verbose_name=_('运营商'), max_length=36, blank=True, default='')
    enable_date = models.DateField(verbose_name=_('开通日期'), null=True, blank=True, default=None)
    is_whithdrawal = models.BooleanField(verbose_name=_('是否撤线'), default=False, help_text=_('0:在网 1:撤线'))
    money = models.DecimalField(
        verbose_name=_('月租费'), max_digits=10, decimal_places=2, null=True, blank=True, default=None, help_text='元')
    remarks = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        ordering = ('-update_time',)
        db_table = 'net_link_lease_line'
        verbose_name = _('租用线路')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.private_line_number


class OpticalFiber(ElementBase):
    """光纤"""

    fiber_cable = models.ForeignKey(
        verbose_name=_('光缆'), to=FiberCable, related_name='fibercable_opticalfiber', db_constraint=False,
        on_delete=models.SET_NULL, null=True, default=None)
    sequence = models.IntegerField(verbose_name=_('纤序'))
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        ordering = ('fiber_cable_id', 'sequence',)
        db_table = 'net_link_optical_fiber'
        verbose_name = _('光纤')
        verbose_name_plural = verbose_name

    def __str__(self):
        if self.fiber_cable:
            return f'{self.fiber_cable.number}: {self.sequence}'

        return str(self.sequence)


class DistriFramePort(ElementBase):
    """配线架端口"""

    number = models.CharField(verbose_name=_('端口编号'), max_length=64, default='', help_text=_('自定义编号'))
    row = models.IntegerField(verbose_name=_('行号'), default=None)
    col = models.IntegerField(verbose_name=_('列号'), default=None)
    distribution_frame = models.ForeignKey(
        verbose_name=_('配线架'), to=DistributionFrame, related_name='distriframe_distriframeport', db_constraint=False,
        on_delete=models.SET_NULL, null=True, default=None)
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        ordering = ('distribution_frame_id', 'row', 'col',)
        db_table = 'net_link_distriframe_port'
        verbose_name = _('配线架端口')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.number


class ConnectorBox(ElementBase):
    """光缆接头盒"""

    number = models.CharField(verbose_name=_('接头盒编号'), max_length=64, default='', help_text=_('自定义编号'))
    place = models.CharField(verbose_name=_('位置'), max_length=128, blank=True, default='')
    remarks = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    location = models.CharField(verbose_name=_('经纬度'), max_length=64, blank=True, default='')
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        ordering = ('-update_time',)
        db_table = 'net_link_connector_box'
        verbose_name = _('光缆接头盒')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.number


class Link(UuidModel):
    """链路表"""

    class LinkStatus(models.TextChoices):
        """链路状态"""
        USING = 'using', _('使用')
        BACKUP = 'backup', _('备用')
        IDLE = 'idle', _('闲置')

    number = models.CharField(verbose_name=_('编号'), max_length=64, default='')
    user = models.CharField(verbose_name=_('用户（单位）'), max_length=128, blank=True, default='')
    endpoint_a = models.CharField(verbose_name=_('A端'), max_length=255, blank=True, default='')
    endpoint_z = models.CharField(verbose_name=_('Z端'), max_length=255, blank=True, default='')
    bandwidth = models.IntegerField(verbose_name=_('带宽'), null=True, blank=True, default=None, help_text='Mbps')
    description = models.CharField(verbose_name=_('用途描述'), max_length=255, blank=True, default='')
    line_type = models.CharField(verbose_name=_('线路类型'), max_length=36, blank=True, default='')
    business_person = models.CharField(verbose_name=_('商务对接'), max_length=36, blank=True, default='')
    build_person = models.CharField(verbose_name=_('线路搭建'), max_length=36, blank=True, default='')
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)
    link_status = models.CharField(
        verbose_name=_('链路状态'), max_length=16, choices=LinkStatus.choices, default=LinkStatus.IDLE)
    remarks = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    enable_date = models.DateField(verbose_name=_('开通日期'), null=True, blank=True, default=None)
    elements = models.ManyToManyField(
        verbose_name=_('网元'), to=Element, through='ElementLink', related_name='links'
    )

    class Meta:
        ordering = ('-update_time',)
        db_table = 'net_link_link'
        verbose_name = _('链路')
        verbose_name_plural = verbose_name

    @property
    def link_element(self):
        return ElementLink.objects.select_related('element').filter(link=self)


class ElementLink(UuidModel):
    """链路网元对应表"""

    element = models.ForeignKey(verbose_name=_('网元'), to=Element, related_name='element_link', on_delete=models.CASCADE)
    link = models.ForeignKey(verbose_name=_('业务链路'), to=Link, related_name='element_link', on_delete=models.CASCADE)
    index = models.IntegerField(verbose_name=_('链路位置'))
    sub_index = models.IntegerField(verbose_name=_('同位编号'), default=1)

    class Meta:
        ordering = ('link_id', 'index', 'sub_index')
        db_table = 'net_link_elementlink'
        verbose_name = _('链路网元对应表')
        verbose_name_plural = verbose_name

    @staticmethod
    def get_linked_object_id_list(object_type: str):
        return ElementLink.objects.filter(element__object_type=object_type).values_list('element__object_id', flat=True)


class ElementDetailData:
    def __init__(self, _type: str = None, lease: LeaseLine = None, fiber: OpticalFiber = None,
                 port: DistriFramePort = None, box: ConnectorBox = None):
        self.type = _type
        self.lease = lease
        self.fiber = fiber
        self.port = port
        self.box = box
