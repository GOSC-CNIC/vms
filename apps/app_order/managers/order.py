from decimal import Decimal
from datetime import datetime
from typing import List, Union

from django.utils.translation import gettext as _
from django.utils import timezone as dj_timezone
from django.db import transaction

from utils.model import OwnerType, PayType
from utils import rand_utils
from apps.app_vo.managers import VoManager
from core import errors
from apps.app_servers.managers import ServiceManager
from apps.app_order.models import Order, Resource, ResourceType
from .instance_configs import (
    BaseConfig, ServerConfig, DiskConfig, BucketConfig, ScanConfig, ServerSnapshotConfig
)
from .price import PriceManager


class OrderManager:
    def create_order(
            self, order_type,
            service_id,
            pay_app_service_id: str,
            service_name,
            resource_type,
            instance_config,
            period,
            period_unit: str,
            pay_type,
            user_id,
            username,
            vo_id,
            vo_name,
            owner_type,
            number: int = 1,
            remark: str = '',
            description: str = ''
    ) -> (Order, List[Resource]):
        """
        提交一个订单

        :instance_config: BaseConfig
        :return:
            order, resources

        :raises: Error
        """
        instance_ids = []
        for x in range(number):
            ins_id = rand_utils.short_uuid1_25()
            if resource_type == ResourceType.VM.value:
                ins_id += '-i'
            elif resource_type == ResourceType.DISK.value:
                ins_id += '-d'
            elif resource_type == ResourceType.VM_SNAPSHOT.value:
                ins_id += '-s'
            else:
                pass

            instance_ids.append(ins_id)

        return self.create_order_for_resources(
            order_type=order_type, pay_type=pay_type,
            pay_app_service_id=pay_app_service_id, service_id=service_id, service_name=service_name,
            resource_type=resource_type, instance_ids=instance_ids, instance_config=instance_config,
            period=period, period_unit=period_unit, start_time=None, end_time=None,
            user_id=user_id, username=username, vo_id=vo_id, vo_name=vo_name, owner_type=owner_type,
            instance_remark=remark, description=description
        )

    def create_renew_order(
            self,
            pay_app_service_id: str, service_id, service_name,
            resource_type, instance_id: str, instance_config,
            period: int, start_time: Union[datetime, None], end_time: Union[datetime, None],
            user_id, username, vo_id, vo_name, owner_type, period_unit=Order.PeriodUnit.MONTH.value,
            description: str = ''
    ) -> (Order, Resource):
        """
        提交一个续费订单

        如果指定续费时长period, 必须start_time = end_time = None；
        如果指定续费到期日期，start_time 和 end_time必须同时有效， period=0

        :instance_id: 续费的实例id of (server, disk)
        :instance_config: BaseConfig
        :return:
            order, resource

        :raises: Error
        """
        if period:
            days = PriceManager.convert_period_days(period=period, period_unit=period_unit)
        else:
            if not (start_time and end_time):
                raise errors.Error(message=_('无法创建订单，必须同时指定时段起始和终止时间。'))

            days = (end_time - start_time).days

        if days > 365 * 2:
            raise errors.ConflictError(message=_('单次续费时长不能超过2年'), code='PeriodTooLong')

        order, resources = self.create_order_for_resources(
            order_type=Order.OrderType.RENEWAL.value, pay_type=PayType.PREPAID.value,
            pay_app_service_id=pay_app_service_id, service_id=service_id, service_name=service_name,
            resource_type=resource_type, instance_ids=[instance_id], instance_config=instance_config,
            period=period, period_unit=period_unit, start_time=start_time, end_time=end_time,
            user_id=user_id, username=username, vo_id=vo_id, vo_name=vo_name, owner_type=owner_type,
            instance_remark='renew', description=description
        )
        return order, resources[0]

    def create_change_pay_type_order(
            self, pay_type: str,
            pay_app_service_id: str, service_id, service_name,
            resource_type, instance_id: str, instance_config,
            period, user_id, username, vo_id, vo_name, owner_type,
            description: str = ''
    ) -> (Order, Resource):
        """
        提交一个修改计费方式订单

        :pay_type: prepaid(按量转包年包月)，postpaid(包年包月转按量)
        :instance_id: 续费的实例id of (server, disk)
        :instance_config: BaseConfig
        :return:
            order, resource

        :raises: Error
        """
        if pay_type == PayType.PREPAID.value:
            order_type = Order.OrderType.POST2PRE.value
        # elif pay_type == PayType.POSTPAID.value:
        #     order_type = Order.OrderType.PRE2POST.value
        else:
            raise errors.Error(message='invalid pay_type')

        order, resources = self.create_order_for_resources(
            order_type=order_type, pay_type=pay_type,
            pay_app_service_id=pay_app_service_id, service_id=service_id, service_name=service_name,
            resource_type=resource_type, instance_ids=[instance_id], instance_config=instance_config,
            period=period, period_unit=Order.PeriodUnit.MONTH.value, start_time=None, end_time=None,
            user_id=user_id, username=username, vo_id=vo_id, vo_name=vo_name, owner_type=owner_type,
            instance_remark='post2prepaid', description=description
        )
        return order, resources[0]

    @staticmethod
    def _check_period_time(order_type: str, pay_type: str, period: int, period_unit: str, start_time, end_time):
        if period < 0:
            raise errors.Error(message=_('无法创建订单，时长不能小于0。'))

        if period_unit not in Order.PeriodUnit.values:
            raise errors.Error(message=_('无法创建订单，订购时长单位无效。'))

        if order_type == Order.OrderType.RENEWAL.value:
            if period and (start_time or end_time):
                raise errors.Error(message=_('无法创建订单，不能同时指定时段起止时间和时长。'))

            if start_time or end_time:
                if not (start_time and end_time):
                    raise errors.Error(message=_('无法创建订单，必须同时指定时段起始和终止时间。'))

                if end_time <= start_time:
                    raise errors.Error(message=_('无法创建订单，时间段不合法，时段终止时间不应小于起始时间。'))

                delta = end_time - start_time
                days = delta.days + delta.seconds / (3600 * 24)
                period = 0
            elif period > 0:
                days = 0
            else:
                raise errors.Error(message=_('无法创建订单，时长必须大于0。'))
        else:
            if start_time or end_time:
                raise errors.Error(message=_('无法创建订单，只有续费订单可以指定时段起止时间。'))

            days = 0

        if pay_type == PayType.PREPAID.value:         # 预付费
            if period == 0 and days == 0:
                raise errors.Error(message=_('无法创建订单，必须指定时段或者时长。'))

        return period, days

    def create_order_for_resources(
            self, order_type, pay_type,
            pay_app_service_id: str, service_id, service_name,
            resource_type, instance_ids: List[str], instance_config,
            period: int, period_unit: str, start_time, end_time,
            user_id, username, vo_id, vo_name, owner_type,
            instance_remark: str = '', description: str = ''
    ) -> (Order, List[Resource]):
        """
        为资源实例提交一个订单，新购、续费、按量转包年包月

        # 续费
            * 如果指定续费时长period, 必须start_time = end_time = None；
            * 如果指定续费到期日期，start_time 和 end_time必须同时有效， period=0
        # 新购、按量转包年包月
            * 只能指定续费时长period, 必须start_time = end_time = None；

        :order_type: 订单类型
        :pay_type: 资源付费方式，预付费时会跟时长和资源类型配置计算金额
        :pay_app_service_id: 资源实例所属服务单元对应的余额结算里的app子服务id
        :service_id: 资源实例所属服务单元id
        :resource_type: 资源实例类型
        :instance_ids: 资源实例ids of (server, disk), list长度为订购数量
        :instance_config: BaseConfig
        :period: 时长，月数
        :description: 订单描述备注信息
        :return:
            order, resources: list

        :raises: Error
        """
        if not instance_ids:
            raise errors.Error(message=_('无法创建订单，必须指定订单资源实例id'))

        number = len(instance_ids)
        if number != len(set(instance_ids)):
            raise errors.Error(message=_('无法创建订单，指定订单资源实例id有重复'))

        # scan支持同时创建web和host 2个任务，instance_ids长度可能为2
        if resource_type == ResourceType.SCAN.value:
            number = 1
            period = days = 0
        else:
            period, days = self._check_period_time(
                order_type=order_type, period=period, period_unit=period_unit,
                start_time=start_time, end_time=end_time, pay_type=pay_type)

        if resource_type == ResourceType.VM_SNAPSHOT.value:
            if number != 1:
                raise errors.Error(message=_('无法创建订单，快照订购数量必须为1'))

        if owner_type not in OwnerType.values:
            raise errors.Error(message=_('无法创建订单，订单所属类型无效'))

        if resource_type not in ResourceType.values:
            raise errors.Error(message=_('无法创建订单，资源类型无效'))

        if order_type not in Order.OrderType.values:
            raise errors.Error(message=_('无法创建订单，订单类型无效或不支持'))

        if pay_type not in PayType.values:
            raise errors.Error(message=_('无法创建订单，资源计费方式pay_type无效'))
        if pay_type == PayType.PREPAID.value:         # 预付费
            total_amount, trade_price = self.calculate_amount_money(
                resource_type=resource_type, config=instance_config, is_prepaid=True,
                period=period, period_unit=period_unit, days=days)
            if number > 1:
                total_amount = total_amount * number
                trade_price = trade_price * number
        else:
            total_amount = trade_price = Decimal(0)

        order = Order(
            order_type=order_type,
            status=Order.Status.UNPAID.value,
            total_amount=total_amount,
            payable_amount=trade_price,
            pay_amount=Decimal('0'),
            balance_amount=Decimal('0'),
            coupon_amount=Decimal('0'),
            app_service_id=pay_app_service_id,
            service_id=service_id,
            service_name=service_name,
            resource_type=resource_type,
            instance_config=instance_config.to_dict(),
            period=period,
            period_unit=period_unit,
            pay_type=pay_type,
            payment_time=None,
            start_time=start_time,
            end_time=end_time,
            user_id=user_id,
            username=username,
            vo_id=vo_id,
            vo_name=vo_name,
            owner_type=owner_type,
            deleted=False,
            trading_status=Order.TradingStatus.OPENING.value,
            completion_time=None,
            number=number,
            description=description
        )

        resources = []
        with transaction.atomic():
            order.save(force_insert=True)
            for ins_id in instance_ids:
                resource = Resource(
                    order=order, resource_type=resource_type,
                    instance_id=ins_id, instance_remark=instance_remark, desc=''
                )
                resource.save(force_insert=True)
                resources.append(resource)

        return order, resources

    @staticmethod
    def calculate_amount_money(
            resource_type, config: BaseConfig, is_prepaid, period: int, period_unit: str, days: float
    ) -> (Decimal, Decimal):
        """
        计算资源金额
        总时长 = period + days

        :param resource_type: 资源类型， vm、disk
        :param config: 资源配置
        :param is_prepaid: True(预付费)， False(按量计费)
        :param period: 预付费时长
        :param period_unit: 时长单位
        :param days: 预付费时长天数
        """
        if resource_type == ResourceType.VM.value:
            if not isinstance(config, ServerConfig):
                raise errors.Error(message=_('无法计算资源金额，资源类型和资源规格配置不匹配'))

            original_price, trade_price = PriceManager().describe_server_price(
                ram_mib=config.vm_ram_mib, cpu=config.vm_cpu, disk_gib=config.vm_systemdisk_size,
                public_ip=config.vm_public_ip, is_prepaid=is_prepaid, period=period, period_unit=period_unit, days=days
            )
        elif resource_type == ResourceType.DISK.value:
            if not isinstance(config, DiskConfig):
                raise errors.Error(message=_('无法计算资源金额，资源类型和资源规格配置不匹配'))

            original_price, trade_price = PriceManager().describe_disk_price(
                size_gib=config.disk_size, is_prepaid=is_prepaid, period=period, period_unit=period_unit, days=days
            )
        elif resource_type == ResourceType.VM_SNAPSHOT.value:
            if not isinstance(config, ServerSnapshotConfig):
                raise errors.Error(message=_('无法计算资源金额，资源类型和资源规格配置不匹配'))

            original_price, trade_price = PriceManager().describe_snapshot_price(
                disk_gib=config.systemdisk_size, is_prepaid=is_prepaid,
                period=period, period_unit=period_unit, days=days
            )
        elif resource_type == ResourceType.BUCKET.value:
            if not isinstance(config, BucketConfig):
                raise errors.Error(message=_('无法计算资源金额，资源类型和资源规格配置不匹配'))

            original_price = trade_price = Decimal(0)
        elif resource_type == ResourceType.SCAN.value:
            if not isinstance(config, ScanConfig):
                raise errors.Error(message=_('无法计算资源金额，资源类型和资源规格配置不匹配'))

            original_price, trade_price = PriceManager().describe_scan_price(
                has_host=bool(config.host_addr), has_web=bool(config.web_url)
            )
        else:
            raise errors.Error(message=_('无法计算资源金额，资源类型无效'))

        return original_price, trade_price

    def create_scan_order(
            self,
            service_id,
            service_name,
            pay_app_service_id: str,
            instance_config: ScanConfig,
            user_id,
            username
    ) -> (Order, List[Resource]):
        """
        提交一个安全扫描订单

        :service_id: 安全扫描服务id
        :service_name: 安全扫描服务名称
        :pay_app_service_id: 安全扫描服务对应的钱包结算单元id
        :return:
            order, resources

        :raises: Error
        """
        instance_ids = []
        if instance_config.web_url:
            instance_ids.append(rand_utils.short_uuid1_25())

        if instance_config.host_addr:
            instance_ids.append(rand_utils.short_uuid1_25())

        if not instance_ids:
            raise errors.Error(message=_('没有安全扫描任务'))

        return self.create_order_for_resources(
            order_type=Order.OrderType.NEW.value, pay_type=PayType.PREPAID.value,
            pay_app_service_id=pay_app_service_id, service_id=service_id, service_name=service_name,
            resource_type=ResourceType.SCAN.value, instance_ids=instance_ids, instance_config=instance_config,
            period=0, period_unit=Order.PeriodUnit.DAY.value, start_time=None, end_time=None,
            user_id=user_id, username=username, vo_id='', vo_name='', owner_type=OwnerType.USER.value,
            instance_remark=instance_config.remark, description=''
        )

    @staticmethod
    def get_order_queryset():
        return Order.objects.all()

    def filter_order_queryset(
            self, resource_type: str, order_type: str, status: str, time_start, time_end,
            user_id: str = None, vo_id: str = None, is_deleded: bool = None
    ):
        """
        查询用户或vo组的订单查询集
        """
        queryset = self.get_order_queryset()
        if user_id:
            queryset = queryset.filter(user_id=user_id, owner_type=OwnerType.USER.value)

        if vo_id:
            queryset = queryset.filter(vo_id=vo_id, owner_type=OwnerType.VO.value)

        if time_start:
            queryset = queryset.filter(creation_time__gte=time_start)

        if time_end:
            queryset = queryset.filter(creation_time__lte=time_end)

        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)

        if order_type:
            queryset = queryset.filter(order_type=order_type)

        if status:
            queryset = queryset.filter(status=status)

        if is_deleded is not None:
            queryset = queryset.filter(deleted=is_deleded)

        return queryset.order_by('-creation_time')

    def filter_vo_order_queryset(
            self, resource_type: str, order_type: str, status: str, time_start, time_end, user, vo_id: str,
            is_deleded: bool = None
    ):
        """
        查询vo组的订单查询集

        :raises: AccessDenied
        """
        self._has_vo_permission(vo_id=vo_id, user=user)
        return self.filter_order_queryset(
            resource_type=resource_type, order_type=order_type, status=status, time_start=time_start,
            time_end=time_end, vo_id=vo_id, is_deleded=is_deleded
        )

    def admin_filter_order_queryset(
            self, admin_user, resource_type: str, order_type: str, status: str, time_start, time_end, user_id: str, vo_id: str,
            is_deleded: bool = None
    ):
        """
        查询vo组的订单查询集

        :raises: AccessDenied
        """
        qs = self.filter_order_queryset(
            resource_type=resource_type, order_type=order_type, status=status, time_start=time_start,
            time_end=time_end, user_id=user_id, vo_id=vo_id, is_deleded=is_deleded
        )
        if admin_user.is_federal_admin():
            return qs

        # 云主机服务单元
        vm_res_type_values = [ResourceType.VM.value, ResourceType.VM_SNAPSHOT.value, ResourceType.DISK.value]
        if not resource_type:
            service_ids = ServiceManager.get_has_perm_service_ids(user_id=admin_user.id)
            if service_ids:
                qs = qs.filter(
                    service_id__in=service_ids, resource_type__in=vm_res_type_values)
            else:
                qs = qs.none()
        elif resource_type in [ResourceType.VM.value, ResourceType.VM_SNAPSHOT.value, ResourceType.DISK.value]:
            service_ids = ServiceManager.get_has_perm_service_ids(user_id=admin_user.id)
            if service_ids:
                qs = qs.filter(service_id__in=service_ids)
            else:
                qs = qs.none()
        else:
            qs = qs.none()

        return qs

    @staticmethod
    def get_order(order_id: str, select_for_update: bool = False):
        if select_for_update:
            return Order.objects.filter(id=order_id).select_for_update().first()

        return Order.objects.filter(id=order_id).first()

    @staticmethod
    def get_resource(resource_id: str, select_for_update: bool = False):
        if select_for_update:
            return Resource.objects.filter(id=resource_id).select_for_update().first()

        return Resource.objects.filter(id=resource_id).first()

    @staticmethod
    def get_resources(resource_ids: List[str], select_for_update: bool = False) -> List[Resource]:
        if select_for_update:
            qs = Resource.objects.filter(id__in=resource_ids).select_for_update()
        else:
            qs = Resource.objects.filter(id__in=resource_ids)

        qs = qs.distinct()
        return list(qs)

    def get_permission_order(
            self, order_id: str, user, check_permission: bool = True, read_only: bool = True
    ) -> Order:
        """
        查询有访问权限订单

        :param order_id: 订单id
        :param user: 用户对象
        :param check_permission: 是否检测权限
        :param read_only: 用于vo组权限检测；True：只需要访问权限；False: 需要管理权限
        """
        order = self.get_order(order_id=order_id)
        if order is None or order.deleted:
            raise errors.NotFound(_('订单不存在'))

        # check permission
        if check_permission:
            if order.owner_type == OwnerType.USER.value:
                if order.user_id and order.user_id != user.id:
                    raise errors.AccessDenied(message=_('您没有此订单访问权限'))
            elif order.vo_id:
                self._has_vo_permission(vo_id=order.vo_id, user=user, read_only=read_only)

        return order

    def get_order_detail(self, order_id: str, user, check_permission: bool = True, read_only: bool = True):
        """
        查询订单详情

        :param order_id: 订单id
        :param user: 用户对象
        :param check_permission: 是否检测权限
        :param read_only: 用于vo组权限检测；True：只需要访问权限；False: 需要管理权限
        :return:
            order, resources
        """
        order = self.get_permission_order(
            order_id=order_id, user=user, check_permission=check_permission, read_only=read_only)
        resources = Resource.objects.filter(order_id=order_id).all()
        resources = list(resources)
        return order, resources

    def admin_get_order_detail(self, order_id: str, admin_user):
        """
        管理员查询订单详情，需要有管理员

        :param order_id: 订单id
        :param admin_user: 用户对象
        :return:
            order, resources
        :raises: NotFound, AccessDenied
        """
        order = self.get_order(order_id=order_id)
        if order is None or order.deleted:
            raise errors.NotFound(_('订单不存在'))

        if not admin_user.is_federal_admin():
            # 云主机服务单元管理员权限
            if order.resource_type in [ResourceType.VM.value, ResourceType.VM_SNAPSHOT.value, ResourceType.DISK.value]:
                if not ServiceManager.has_perm(user_id=admin_user.id, service_id=order.service_id):
                    raise errors.AccessDenied(message=_('您没有此订单的访问权限，没有订购资源的服务单元的管理权限'))
            else:
                raise errors.AccessDenied(message=_('您没有此订单的访问权限，此订单订购的资源类型的相关订单暂不支持非联邦管理员权限'))

        resources = Resource.objects.filter(order_id=order_id).all()
        resources = list(resources)
        return order, resources

    @staticmethod
    def _has_vo_permission(vo_id, user, read_only: bool = True):
        """
        是否有vo组的权限

        :raises: AccessDenied
        """
        try:
            if read_only:
                VoManager().get_has_read_perm_vo(vo_id=vo_id, user=user)
            else:
                VoManager().get_has_manager_perm_vo(vo_id=vo_id, user=user)
        except errors.Error as exc:
            raise errors.AccessDenied(message=exc.message)

    @staticmethod
    def set_order_resource_deliver_ok(order: Order, resource: Resource, start_time, due_time, instance_id: str = None):
        """
        订单资源交付成功， 更新订单信息

        :return:
            order, resource    # success

        :raises: Error
        """
        message = ''
        with transaction.atomic():
            order = Order.objects.filter(id=order.id).select_for_update().first()
            if order.trading_status in [order.TradingStatus.CLOSED, order.TradingStatus.COMPLETED]:
                raise errors.Error(message=_('交易关闭和交易完成状态的订单不允许修改'))

            now_tm = dj_timezone.now()
            update_fields = ['trading_status', 'completion_time']
            if order.pay_type != PayType.POSTPAID.value:
                order.start_time = start_time
                order.end_time = due_time
                update_fields += ['start_time', 'end_time']

            order.trading_status = order.TradingStatus.COMPLETED.value
            order.completion_time = now_tm
            try:
                order.save(update_fields=update_fields)
            except Exception as e:
                message = _('更新订单交易状态失败') + str(e)

            resource.instance_status = resource.InstanceStatus.SUCCESS.value
            resource.desc = 'success'
            resource.delivered_time = now_tm
            update_fields = ['instance_status', 'desc', 'delivered_time']
            if instance_id:
                resource.instance_id = instance_id
                update_fields.append('instance_id')
            try:
                resource.save(update_fields=update_fields)
            except Exception as e:
                message += _('更新订单的资源交付结果失败') + str(e)

        if message:
            raise errors.Error(message=message)

        return order, resource

    @staticmethod
    def set_order_resource_deliver_failed(order: Order, resource: Resource, failed_msg: str):
        """
        订单资源交付失败， 更新订单信息

        :return:
            order, resource    # success

        :raises: Error
        """
        message = ''
        if len(failed_msg) >= 255:
            failed_msg = failed_msg[:255]

        with transaction.atomic():
            order = Order.objects.filter(id=order.id).select_for_update().first()
            if order.trading_status in [order.TradingStatus.CLOSED, order.TradingStatus.COMPLETED]:
                raise errors.Error(message=_('交易关闭和交易完成状态的订单不允许修改'))

            try:
                resource.instance_status = resource.InstanceStatus.FAILED.value
                resource.desc = failed_msg
                resource.save(update_fields=['instance_status', 'desc'])
            except Exception as e:
                message = _('更新订单的资源创建结果失败') + str(e)

            order.trading_status = order.TradingStatus.UNDELIVERED.value
            try:
                order.save(update_fields=['trading_status'])
            except Exception as e:
                message += _('更新订单交易状态失败') + str(e)

        if message:
            raise errors.Error(message=message)

        return order, resource

    @staticmethod
    def set_order_deliver_success(order: Order, select_for_update: bool = True):
        """
        订单资源交付成功， 更新订单信息

        :return:
            order    # success

        :raises: Error
        """
        try:
            if not select_for_update:
                order.set_completed()
                return order

            with transaction.atomic():
                order = Order.objects.filter(id=order.id).select_for_update().first()
                if order.trading_status in [order.TradingStatus.CLOSED, order.TradingStatus.COMPLETED]:
                    raise errors.Error(message=_('交易关闭和交易完成状态的订单不允许修改'))

                order.set_completed()
                return order
        except Exception as exc:
            raise errors.Error.from_error(exc)

    @staticmethod
    def set_order_deliver_failed(order: Order, trading_status: str = Order.TradingStatus.UNDELIVERED.value):
        """
        订单资源交付失败， 更新订单信息

        :return:
            order    # success

        :raises: Error
        """
        with transaction.atomic():
            order = Order.objects.filter(id=order.id).select_for_update().first()
            if order.trading_status in [order.TradingStatus.CLOSED, order.TradingStatus.COMPLETED]:
                raise errors.Error(message=_('交易关闭和交易完成状态的订单不允许修改'))

            order.trading_status = trading_status
            try:
                order.save(update_fields=['trading_status'])
            except Exception as e:
                raise errors.Error(message=_('更新订单交易状态失败') + str(e))

        return order

    @staticmethod
    def _can_cancel_order_check(order: Order):
        if order.trading_status == order.TradingStatus.CLOSED.value:
            raise errors.OrderTradingClosed(message=_('订单交易已关闭'))
        elif order.trading_status == order.TradingStatus.COMPLETED.value:
            raise errors.OrderTradingCompleted(message=_('订单交易已完成'))

        if order.status == Order.Status.PAID.value:
            raise errors.OrderPaid(message=_('订单已支付'))
        elif order.status == Order.Status.CANCELLED.value:
            raise errors.OrderCancelled(message=_('订单已作废'))
        elif order.status in [Order.Status.REFUND.value, Order.Status.PART_REFUND.value]:
            raise errors.OrderRefund(message=_('订单已退款'))
        elif order.status == Order.Status.REFUNDING.value:
            raise errors.OrderRefund(message=_('订单正在退款中'))
        elif order.status != Order.Status.UNPAID.value:
            raise errors.OrderStatusUnknown(message=_('未知状态的订单'))

        if order.order_action == Order.OrderAction.DELIVERING.value:
            raise errors.TryAgainLater(message=_('正在交付订单资源，请稍后重试'))

    def cancel_order(self, order_id: str, user):
        """
        取消作废订单

        :return:
            order
        :raises: Error
        """
        order = self.get_permission_order(
            order_id=order_id, user=user, check_permission=True, read_only=False)
        self._can_cancel_order_check(order=order)
        return self.do_cancel_order(order_id=order.id)

    def do_cancel_order(self, order_id: str):
        try:
            with transaction.atomic():
                order = self.get_order(order_id=order_id, select_for_update=True)
                if order.deleted:
                    raise errors.NotFound(_('订单不存在'))

                self._can_cancel_order_check(order=order)

                try:
                    order.set_cancel()
                except Exception as e:
                    raise errors.Error(message=_('更新订单状态错误。') + str(e))

                return order
        except errors.Error as exc:
            raise exc
        except Exception as exc:
            raise errors.Error(message=str(exc))

    @staticmethod
    def get_order_resources(order_id: str, select_for_update: bool = False) -> List[Resource]:
        if select_for_update:
            qs = Resource.objects.filter(order_id=order_id).select_for_update().all()
        else:
            qs = Resource.objects.filter(order_id=order_id).all()

        qs = qs.distinct()
        return list(qs)

    @staticmethod
    def set_resource_instance_deleted(resource_type: str, instance_id: str, raise_exc: bool):
        """
        资源实例删除时，标记对应的订单资源记录资源实例删除的时间
        """
        try:
            return Resource.objects.filter(
                resource_type=resource_type, instance_id=instance_id).update(instance_delete_time=dj_timezone.now())
        except Exception as exc:
            if raise_exc:
                raise exc

    @staticmethod
    def set_resource_server_deleted(instance_id: str, raise_exc: bool):
        """
        资源实例删除时，标记对应的订单资源记录资源实例删除的时间
        """
        return OrderManager.set_resource_instance_deleted(
            resource_type=ResourceType.VM.value, instance_id=instance_id, raise_exc=raise_exc)

    @staticmethod
    def set_resource_disk_deleted(instance_id: str, raise_exc: bool):
        """
        资源实例删除时，标记对应的订单资源记录资源实例删除的时间
        """
        return OrderManager.set_resource_instance_deleted(
            resource_type=ResourceType.DISK.value, instance_id=instance_id, raise_exc=raise_exc)

    @staticmethod
    def can_deliver_or_refund_for_order(order: Order):
        """
        检查订单状态是否满足资源交付或者退订条件

        :return:
            True    # 满足
            raise Error # 不满足
        """
        if order.trading_status == order.TradingStatus.CLOSED.value:
            raise errors.OrderTradingClosed(message=_('订单交易已关闭'))
        elif order.trading_status == order.TradingStatus.COMPLETED.value:
            raise errors.OrderTradingCompleted(message=_('订单交易已完成'))

        if order.status == Order.Status.UNPAID.value:
            raise errors.OrderUnpaid(message=_('订单未支付'))
        elif order.status == Order.Status.CANCELLED.value:
            raise errors.OrderCancelled(message=_('订单已作废'))
        elif order.status in [Order.Status.REFUND.value, Order.Status.PART_REFUND.value]:
            raise errors.OrderRefund(message=_('订单已退款'))
        elif order.status == Order.Status.REFUNDING.value:
            raise errors.OrderRefund(message=_('订单正在退款中'))
        elif order.status != Order.Status.PAID.value:
            raise errors.OrderStatusUnknown(message=_('未知状态的订单'))

        if order.order_action == Order.OrderAction.DELIVERING.value:
            raise errors.ConflictError(message=_('订单资源正在交付中'), code='OrderDelivering')
        elif order.order_action != Order.OrderAction.NONE.value:
            raise errors.ConflictError(
                message=_('订单处在未知的操作动作中，请稍后重试，或者联系客服人员人工处理。'), code='OrderActionUnknown')

        return True

    @staticmethod
    def set_order_refund_success(order: Order, is_part_refund: bool):
        """
        订单退订成功，更新订单信息

        * 订单状态更新操作尽量加锁 放在一个事务中执行
        :return:
            order    # success

        :raises: Error
        """
        if order.trading_status in [order.TradingStatus.CLOSED, order.TradingStatus.COMPLETED]:
            raise errors.Error(message=_('交易关闭和交易完成状态的订单不允许修改'))

        update_fields = ['trading_status', 'status']
        order.trading_status = order.TradingStatus.COMPLETED.value
        if is_part_refund:
            order.status = Order.Status.PART_REFUND.value
        else:
            order.status = Order.Status.REFUND.value

        try:
            order.save(update_fields=update_fields)
        except Exception as e:
            message = _('更新订单交易状态失败') + str(e)
            raise errors.Error(message=message)

        return order

    @staticmethod
    def _can_delete_order_check(order: Order):
        if order.trading_status not in [order.TradingStatus.CLOSED.value, order.TradingStatus.COMPLETED.value]:
            raise errors.ConflictError(message=_('只允许删除交易已关闭、已完成的订单'), code='ConflictTradingStatus')

        if order.status == Order.Status.UNPAID.value:
            raise errors.OrderUnpaid(message=_('未支付状态的订单，请先取消订单后再尝试删除'))
        elif order.status == Order.Status.PAID.value:
            if order.trading_status not in [order.TradingStatus.CLOSED.value, order.TradingStatus.COMPLETED.value]:
                raise errors.OrderPaid(message=_('已支付状态的订单，资源交付未完成，请先退订退款后再尝试删除'))
        elif order.status == Order.Status.REFUNDING.value:
            raise errors.OrderRefund(message=_('订单正在退款中，请稍后重试'))
        elif order.status not in [
            Order.Status.CANCELLED.value, Order.Status.REFUND.value, Order.Status.PART_REFUND.value
        ]:
            raise errors.OrderStatusUnknown(message=_('未知状态的订单'))

        if order.order_action == Order.OrderAction.DELIVERING.value:
            raise errors.TryAgainLater(message=_('正在交付订单资源，请稍后重试'))

    def delete_order(self, order_id: str, user):
        """
        取消作废订单

        :return:
            order
        :raises: Error
        """
        order = self.get_permission_order(
            order_id=order_id, user=user, check_permission=True, read_only=False)
        self._can_delete_order_check(order=order)
        return self.do_delete_order(order_id=order.id)

    def do_delete_order(self, order_id: str):
        try:
            with transaction.atomic():
                order = self.get_order(order_id=order_id, select_for_update=True)
                if order.deleted:
                    return order

                self._can_delete_order_check(order=order)

                try:
                    order.deleted = True
                    order.save(update_fields=['deleted'])
                except Exception as e:
                    raise errors.Error(message=_('更新订单错误。') + str(e))

                return order
        except errors.Error as exc:
            raise exc
        except Exception as exc:
            raise errors.Error(message=str(exc))
