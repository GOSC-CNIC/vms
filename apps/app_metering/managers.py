from datetime import date

from django.utils.translation import gettext as _
from django.db.models import Subquery, Sum, Count

from core import errors
from apps.app_servers.managers import ServiceManager
from apps.app_servers.models import ServiceConfig
from apps.app_servers.managers import ServerManager, DiskManager
from apps.app_servers.models import Server, ServerArchive, Disk
from utils.model import OwnerType
from apps.app_users.models import UserProfile
from apps.app_vo.models import VirtualOrganization
from apps.app_vo.managers import VoManager
from apps.app_storage.managers.objects_service import ObjectsServiceManager
from apps.app_storage.models import Bucket, BucketArchive, ObjectsService

from .models import (
    MeteringServer, MeteringObjectStorage, MeteringDisk, MeteringMonitorWebsite,
    DailyStatementServer, DailyStatementObjectStorage, DailyStatementDisk, DailyStatementMonitorWebsite,
)


class BaseMeteringManager:
    AGGREGATION_USER_ORDER_BY_CHOICES = [
        'total_original_amount', '-total_original_amount'
    ]
    AGGREGATION_VO_ORDER_BY_CHOICES = [
        'total_original_amount', '-total_original_amount'
    ]
    AGGREGATION_SERVICE_ORDER_BY_CHOICES = [
        'total_original_amount', '-total_original_amount'
    ]

    @staticmethod
    def aggregate_by_user_mixin_data(data: list):
        """
        按user id聚合数据分页后混合其他数据
        """
        user_ids = [i['user_id'] for i in data]
        users = UserProfile.objects.filter(id__in=user_ids).values('id', 'username', 'company')

        user_dict = {}
        for user in users:
            user_id = user['id']
            u = {
                'user': user
            }
            user_dict[user_id] = u

        for i in data:
            i: dict
            i.update(user_dict[i['user_id']])

        return data

    @staticmethod
    def aggregate_by_vo_mixin_data(data: list):
        """
        按vo id聚合数据分页后混合其他数据
        """
        vo_ids = [i['vo_id'] for i in data]
        vos = VirtualOrganization.objects.filter(id__in=vo_ids).values('id', 'name', 'company')

        vo_dict = {}
        for vo in vos:
            vo_id = vo['id']
            v = {
                'vo': vo
            }
            vo_dict[vo_id] = v

        for i in data:
            if i['vo_id'] in vo_dict:
                i.update(vo_dict[i['vo_id']])
            else:
                i['vo'] = None

        return data

    @staticmethod
    def aggregate_by_service_mixin_data(data: list):
        """
        按service id聚合数据分页后混合其他数据
        """
        service_ids = [i['service_id'] for i in data]
        services = ServiceConfig.objects.filter(id__in=service_ids).values('id', 'name')

        service_dict = {}
        for service in services:
            service_id = service['id']
            s = {
                'service': service
            }
            service_dict[service_id] = s

        for i in data:
            i: dict
            i.update(service_dict[i['service_id']])

        return data


class MeteringServerManager(BaseMeteringManager):
    @staticmethod
    def get_metering_server_queryset():
        return MeteringServer.objects.all()

    @staticmethod
    def get_metering_by_id(metering_id: str) -> MeteringServer:
        return MeteringServer.objects.filter(id=metering_id).first()

    @staticmethod
    def get_metering(metering_id: str, user):
        """
        查询一个计量单，检查权限

        :raises: Error
        """
        metering = MeteringServerManager.get_metering_by_id(metering_id=metering_id)
        if metering is None:
            raise errors.NotFound(message=_('计量单不存在。'))

        if metering.owner_type == metering.OwnerType.USER.value:
            if metering.user_id != user.id:
                raise errors.AccessDenied(message=_('无计量单的访问权限。'))
        elif metering.owner_type == metering.OwnerType.VO.value:
            VoManager().get_has_read_perm_vo(vo_id=metering.vo_id, user=user)

        return metering

    def filter_user_server_metering(
            self, user,
            service_id: str = None,
            server_id: str = None,
            date_start: date = None,
            date_end: date = None
    ):
        """
        查询用户云主机计量用量账单查询集
        """
        return self.filter_server_metering_queryset(
            service_id=service_id, server_id=server_id, date_start=date_start,
            date_end=date_end, user_id=user.id
        )

    def filter_vo_server_metering(
            self, user,
            vo_id: str,
            service_id: str = None,
            server_id: str = None,
            date_start: date = None,
            date_end: date = None
    ):
        """
        查询vo组云主机计量用量账单查询集

        :rasies: AccessDenied, NotFound, Error
        """
        VoManager().get_has_read_perm_vo(vo_id=vo_id, user=user)
        return self.filter_server_metering_queryset(
            service_id=service_id, server_id=server_id, date_start=date_start,
            date_end=date_end, vo_id=vo_id
        )

    def filter_server_metering_by_admin(    
            self, user,
            service_id: str = None,
            server_id: str = None,
            date_start: date = None,
            date_end: date = None,
            vo_id: str = None,
            user_id: str = None
    ):
        """
        查询vo组云主机计量用量账单查询集

        :rasies: AccessDenied, NotFound, Error
        """
        if user.is_federal_admin():     
            return self.filter_server_metering_queryset(
                service_id=service_id, server_id=server_id, date_start=date_start, date_end=date_end,
                vo_id=vo_id, user_id=user_id
            )

        if server_id:                    
            server_or_archieve = ServerManager.get_server_or_archive(server_id=server_id) 
            
            if server_or_archieve is None:         
                return MeteringServer.objects.none()
            
            if service_id:      
                if service_id != server_or_archieve.service_id:
                    return MeteringServer.objects.none()
            else:              
                service_id = server_or_archieve.service_id

        if service_id:      
            service = ServiceManager.get_service_if_admin(user=user, service_id=service_id)
            if service is None:
                raise errors.AccessDenied(message=_('您没有指定服务的访问权限'))

        queryset = self.filter_server_metering_queryset(
                service_id=service_id, server_id=server_id, date_start=date_start, date_end=date_end,
                vo_id=vo_id, user_id=user_id
            )

        if not service_id and not server_id:
            qs = ServiceManager.get_all_has_perm_service(user)
            subq = Subquery(qs.values_list('id', flat=True))
            queryset = queryset.filter(service_id__in=subq)

        return queryset

    def filter_server_metering_queryset(       
            self, service_id: str = None,
            server_id: str = None,
            date_start: date = None,
            date_end: date = None,
            user_id: str = None,
            vo_id: str = None
    ):
        """
        查询云主机计量用量账单查询集
        """
        if user_id and vo_id:
            raise errors.Error(_('云主机计量用量账单查询集查询条件不能同时包含"user_id"和"vo_id"'))

        lookups = {}
        if date_start:
            lookups['date__gte'] = date_start

        if date_end:
            lookups['date__lte'] = date_end

        if service_id:
            lookups['service_id'] = service_id

        if server_id:
            lookups['server_id'] = server_id

        if user_id:
            lookups['owner_type'] = OwnerType.USER.value
            lookups['user_id'] = user_id

        if vo_id:
            lookups['owner_type'] = OwnerType.VO.value
            lookups['vo_id'] = vo_id

        queryset = self.get_metering_server_queryset()      
        return queryset.filter(**lookups).order_by('-creation_time')    

    def aggregate_server_metering_by_uuid_by_admin(
            self, user,
            date_start: date = None,
            date_end: date = None,
            user_id: str = None,
            service_id: str = None,
            vo_id: str = None
    ):
        """
            管理员获取以server_id聚合的查询集
        """
        if user.is_federal_admin():
            queryset = self.filter_server_metering_queryset(
                service_id=service_id, date_start=date_start, date_end=date_end, user_id=user_id, vo_id=vo_id
            )
            return self.aggregate_queryset_by_server(queryset)

        if service_id:
            service = ServiceManager.get_service_if_admin(user=user, service_id=service_id)
            if service is None:
                raise errors.AccessDenied(message=_('您没有指定服务的访问权限'))

        queryset = self.filter_server_metering_queryset(
            service_id=service_id, date_start=date_start, date_end=date_end, user_id=user_id, vo_id=vo_id
        )

        if not service_id:
            qs = ServiceManager.get_all_has_perm_service(user)  
            subq = Subquery(qs.values_list('id', flat=True))   
            queryset = queryset.filter(service_id__in=subq)

        return self.aggregate_queryset_by_server(queryset)

    def aggregate_server_metering_by_uuid_by_user(
            self, user,
            date_start: date = None,
            date_end: date = None,
            service_id: str = None
    ):
        """
        普通用户获取自己名下以server_id聚合的查询集
        """
        queryset = self.filter_server_metering_queryset(
            service_id=service_id, date_start=date_start,
            date_end=date_end, user_id=user.id
        )
        return self.aggregate_queryset_by_server(queryset)

    def aggregate_server_metering_by_uuid_by_vo(
            self, user,
            date_start: date = None,
            date_end: date = None,
            service_id: str = None,
            vo_id: str = None
    ):
        """
        指定vo组下以server_id聚合的查询集
        """
        VoManager().get_has_read_perm_vo(vo_id=vo_id, user=user)
        queryset = self.filter_server_metering_queryset(
            service_id=service_id, date_start=date_start,
            date_end=date_end, vo_id=vo_id
        )
        return self.aggregate_queryset_by_server(queryset)

    @staticmethod
    def aggregate_queryset_by_server(queryset):
        """
        聚合云主机计量数据
        """
        queryset = queryset.values('server_id').annotate(   
            total_cpu_hours=Sum('cpu_hours'),
            total_ram_hours=Sum('ram_hours'),
            total_disk_hours=Sum('disk_hours'),
            total_public_ip_hours=Sum('public_ip_hours'),
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount')
        ).order_by('server_id')

        return queryset

    @staticmethod
    def aggregate_by_server_mixin_data(data: list):
        """
        按server id聚合数据分页后混合其他数据
        """
        server_ids = [i['server_id'] for i in data]
        servers = Server.objects.filter(id__in=server_ids).values(
            'id', 'ipv4', 'ram', 'vcpus', 'service_id', 'service__name')
        archives = ServerArchive.objects.filter(
            server_id__in=server_ids, archive_type=ServerArchive.ArchiveType.ARCHIVE.value
        ).values('server_id', 'ipv4', 'ram', 'vcpus', 'service_id', 'service__name')

        server_dict = {}
        for s in servers:
            d = {
                'service_id': s.pop('service_id', None),
                'service_name': s.pop('service__name', None),
                'server': s
            }
            server_dict[s['id']] = d

        for a in archives:
            server_id = a['id'] = a.pop('server_id', None)
            if server_id and server_id not in server_dict:
                d = {
                    'service_id': a.pop('service_id', None),
                    'service_name': a.pop('service__name', None),
                    'server': a
                }
                server_dict[server_id] = d

        for i in data:
            i: dict
            sid = i['server_id']
            if sid in server_dict:
                i.update(server_dict[sid])
            else:
                i['service_id'] = None
                i['service_name'] = None
                i['server'] = None

        return data

    def aggregate_server_metering_by_userid_by_admin(
            self, user,
            date_start: date = None,
            date_end: date = None,
            service_id: str = None,
            order_by: str = None
    ):
        """
            管理员获取以user_id聚合的查询集
        """
        queryset = self.filter_server_metering_queryset(   
            date_start=date_start, date_end=date_end, service_id=service_id
        ).filter(owner_type=OwnerType.USER.value)

        if user.is_federal_admin():
            return self.aggregate_queryset_by_user(queryset, order_by=order_by)
        
        if service_id:
            service = ServiceManager.get_service_if_admin(user=user, service_id=service_id)
            if service is None:
                raise errors.AccessDenied(message=_('您没有指定服务的访问权限'))
        else:
            qs = ServiceManager.get_all_has_perm_service(user)  
            subq = Subquery(qs.values_list('id', flat=True))
            queryset = queryset.filter(service_id__in=subq)

        return self.aggregate_queryset_by_user(queryset, order_by=order_by)

    @staticmethod
    def aggregate_queryset_by_user(queryset, order_by: str = None):
        """
        聚合用户的云主机计量数据
        """
        if not order_by:
            order_by = 'user_id'

        queryset = queryset.values('user_id').annotate(
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount'),
            total_server=Count('server_id', distinct=True),
        ).order_by(order_by)

        return queryset

    def aggregate_server_metering_by_void_by_admin(
            self, user,
            date_start: date = None,
            date_end: date = None,
            service_id: str = None,
            order_by: str = None
    ):
        """
            管理员获取以vo_id聚合的查询集
        """
        queryset = self.filter_server_metering_queryset(   
            date_start=date_start, date_end=date_end, service_id=service_id
        ).filter(owner_type=OwnerType.VO.value)              
        
        if user.is_federal_admin():     
            return self.aggregate_queryset_by_vo(queryset, order_by=order_by)
        
        if service_id:      
            service = ServiceManager.get_service_if_admin(user=user, service_id=service_id)
            if service is None:
                raise errors.AccessDenied(message=_('您没有指定服务的访问权限'))
        else:       
            qs = ServiceManager.get_all_has_perm_service(user)  
            subq = Subquery(qs.values_list('id', flat=True))   
            queryset = queryset.filter(service_id__in=subq)

        return self.aggregate_queryset_by_vo(queryset, order_by=order_by)

    @staticmethod
    def aggregate_queryset_by_vo(queryset, order_by: str = None):
        """
        聚合vo组的云主机计量数据
        """
        if not order_by:
            order_by = 'vo_id'

        queryset = queryset.values('vo_id').annotate(
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount'),
            total_server=Count('server_id', distinct=True),
        ).order_by(order_by)

        return queryset

    def aggregate_server_metering_by_serviceid_by_admin(
            self, user,
            date_start: date = None,
            date_end: date = None,
            order_by: str = None
    ):
        """
            管理员获取以service_id聚合的查询集
        """
        queryset = self.filter_server_metering_queryset(    
            date_start=date_start, date_end=date_end, 
        )      
        
        if user.is_federal_admin():     
            return self.aggregate_queryset_by_service(queryset, order_by=order_by)
        
        qs = ServiceManager.get_all_has_perm_service(user)  
        subq = Subquery(qs.values_list('id', flat=True))   
        queryset = queryset.filter(service_id__in=subq)

        return self.aggregate_queryset_by_service(queryset, order_by=order_by)

    @staticmethod
    def aggregate_queryset_by_service(queryset, order_by: str = None):
        """
        聚合服务节点的云主机计量数据
        """
        if not order_by:
            order_by = 'service_id'

        queryset = queryset.values('service_id').annotate(
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount'),
            total_server=Count('server_id', distinct=True),
        ).order_by(order_by)

        return queryset

    @staticmethod
    def get_meterings_by_statement_id(statement_id: str, _date: date):
        queryset = MeteringServerManager.get_metering_server_queryset()
        return queryset.filter(date=_date, daily_statement_id=statement_id)


class BaseStatementManager:
    @staticmethod
    def filter_statement_queryset(
            queryset, payment_status: str, date_start, date_end,
            user_id: str = None, vo_id: str = None
    ):
        if user_id:
            queryset = queryset.filter(user_id=user_id, owner_type=OwnerType.USER.value)

        if vo_id:
            queryset = queryset.filter(vo_id=vo_id, owner_type=OwnerType.VO.value)

        if date_start:
            queryset = queryset.filter(date__gte=date_start)

        if date_end:
            queryset = queryset.filter(date__lte=date_end)

        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)

        return queryset.order_by('-creation_time')

    @staticmethod
    def has_vo_permission(vo_id, user, read_only: bool = True):
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


class StatementServerManager(BaseStatementManager):
    @staticmethod
    def get_statement_server_queryset():
        return DailyStatementServer.objects.all()
    
    def filter_statement_server_queryset(
            self, payment_status: str, date_start, date_end,
            user_id: str = None, vo_id: str = None
    ):
        """
        查询用户或vo组的日结算单查询集
        """
        queryset = self.get_statement_server_queryset()
        return self.filter_statement_queryset(
            queryset=queryset, payment_status=payment_status, date_start=date_start, date_end=date_end,
            user_id=user_id, vo_id=vo_id
        )

    def filter_vo_statement_server_queryset(
        self, payment_status: str, date_start, date_end, user, vo_id: str
    ):
        """
        查询vo组的日结算单查询集

        :raises: AccessDenied
        """
        self.has_vo_permission(vo_id=vo_id, user=user)
        return self.filter_statement_server_queryset(
            payment_status=payment_status, date_start=date_start,
            date_end=date_end, vo_id=vo_id
        )

    @staticmethod
    def get_statement_server(statement_id: str, select_for_update: bool = False):
        if select_for_update:
            return DailyStatementServer.objects.filter(
                id=statement_id
            ).select_related('service').select_for_update().first()

        return DailyStatementServer.objects.filter(id=statement_id).select_related('service').first()

    def get_statement_server_detail(
            self, statement_id: str, user, check_permission: bool = True, read_only: bool = True
    ):
        """
        查询日结算单详情

        :param check_permission: 是否检测权限
        :param read_only: 用于vo组权限检测；True：只需要访问权限；False: 需要管理权限
        :return:
            statement_server
        """
        statement = self.get_statement_server(statement_id=statement_id)
        if statement is None:
            raise errors.NotFound(_('日结算单不存在'))

        # check permission
        if check_permission:
            if statement.owner_type == OwnerType.USER.value:
                if statement.user_id and statement.user_id != user.id:
                    raise errors.AccessDenied(message=_('您没有此日结算单访问权限'))
            elif statement.vo_id:
                self.has_vo_permission(vo_id=statement.vo_id, user=user, read_only=read_only)

        return statement


class MeteringStorageManager:
    @staticmethod
    def get_metering_obs_queryset():
        return MeteringObjectStorage.objects.select_related('service').all()

    def filter_user_storage_metering(
            self, user,
            service_id: str = None,
            bucket_id: str = None,
            date_start: date = None,
            date_end: date = None
    ):
        """
        查询用户的对象存储的计量账单的查询集合
        """
        return self.filter_obs_metering_queryset(
            service_id=service_id, bucket_id=bucket_id, date_start=date_start,
            date_end=date_end, user_id=user.id
        )

    def filter_storage_metering_by_admin(
            self, user,
            service_id: str = None,
            bucket_id: str = None,
            date_start: date = None,
            date_end: date = None,
            user_id: str = None
    ):
        """
        查询用户的对象存储的计量账单的查询集合
        :return: QuerySet()
        :raises: Error
        """
        if user.is_federal_admin():
            return self.filter_obs_metering_queryset(
                service_id=service_id, bucket_id=bucket_id, date_start=date_start,
                date_end=date_end, user_id=user_id
            )

        if service_id:
            service = ObjectsServiceManager.get_service_if_admin(user=user, service_id=service_id)
            if service is None:
                raise errors.AccessDenied(message=_('您没有指定服务的访问权限'))

        queryset = self.filter_obs_metering_queryset(
            service_id=service_id, date_start=date_start, date_end=date_end, user_id=user_id, bucket_id=bucket_id
        )

        if not service_id:
            qs = ObjectsServiceManager.get_all_has_perm_service(user)
            subq = Subquery(qs.values_list('id', flat=True))
            queryset = queryset.filter(service_id__in=subq)

        return queryset

    def filter_obs_metering_queryset(
            self, service_id: str = None,
            bucket_id: str = None,
            date_start: date = None,
            date_end: date = None,
            user_id: str = None
    ):
        lookups = {}
        if user_id:
            lookups['user_id'] = user_id

        if service_id:
            lookups['service_id'] = service_id

        if bucket_id:
            lookups['storage_bucket_id'] = bucket_id

        if date_start:
            lookups['date__gte'] = date_start

        if date_end:
            lookups['date__lte'] = date_end

        queryset = self.get_metering_obs_queryset()
        return queryset.filter(**lookups).order_by('-creation_time')

    @staticmethod
    def get_meterings_by_statement_id(statement_id: str, _date: date):
        return MeteringObjectStorage.objects.filter(date=_date, daily_statement_id=statement_id)

    def admin_aggregate_metering_by_bucket(
            self, user,
            date_start: date = None,
            date_end: date = None,
            user_id: str = None,
            service_id: str = None,
            bucket_id: str = None,
            order_by: str = None
    ):
        """
            管理员获取以bucket聚合的查询集
        """
        if user.is_federal_admin():
            queryset = self.filter_obs_metering_queryset(
                service_id=service_id, date_start=date_start, date_end=date_end, user_id=user_id, bucket_id=bucket_id
            )
            return self._aggregate_queryset_by_bucket(queryset, order_by=order_by)

        if service_id:
            service = ObjectsServiceManager.get_service_if_admin(user=user, service_id=service_id)
            if service is None:
                raise errors.AccessDenied(message=_('您没有指定服务的访问权限'))

        queryset = self.filter_obs_metering_queryset(
            service_id=service_id, date_start=date_start, date_end=date_end, user_id=user_id, bucket_id=bucket_id
        )

        if not service_id:
            qs = ObjectsServiceManager.get_all_has_perm_service(user)
            subq = Subquery(qs.values_list('id', flat=True))
            queryset = queryset.filter(service_id__in=subq)

        return self._aggregate_queryset_by_bucket(queryset, order_by=order_by)

    AGGREGATION_BUCKET_ORDER_BY_CHOICES = [
        'total_original_amount', '-total_original_amount', 'total_storage_hours', '-total_storage_hours'
    ]

    @staticmethod
    def _aggregate_queryset_by_bucket(queryset, order_by: str):
        """
        聚合bucket计量数据
        """
        if not order_by:
            order_by = 'storage_bucket_id'

        queryset = queryset.values('storage_bucket_id').annotate(
            total_storage_hours=Sum('storage'),
            total_downstream=Sum('downstream'),
            total_get_request=Sum('get_request'),
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount')
        ).order_by(order_by)

        return queryset

    @staticmethod
    def aggregate_by_bucket_mixin_data(data: list):
        """
        按bucket聚合数据分页后混合其他数据
        """
        bucket_ids = [i['storage_bucket_id'] for i in data]
        buckets = Bucket.objects.filter(
            id__in=bucket_ids).values(
            'id', 'name', 'storage_size', 'object_count', 'stats_time', 'tag',
            'user__id', 'user__username', 'service__id', 'service__name')
        archives = BucketArchive.objects.filter(
            original_id__in=bucket_ids,
        ).values(
            'original_id', 'name', 'storage_size', 'object_count', 'stats_time', 'tag',
            'user__id', 'user__username', 'service__id', 'service__name')

        buckets_dict = {}
        for s in buckets:
            user = {'id': s.pop('user__id', None), 'username': s.pop('user__username', None)}
            service = {'id': s.pop('service__id', None), 'name': s.pop('service__name', None)}
            d = {
                'service': service,
                'user': user,
                'bucket': s
            }
            buckets_dict[s['id']] = d

        for a in archives:
            server_id = a['id'] = a.pop('original_id', None)
            if server_id and server_id not in buckets_dict:
                user = {'id': a.pop('user__id', None), 'username': a.pop('user__username', None)}
                service = {'id': a.pop('service__id', None), 'name': a.pop('service__name', None)}
                d = {
                    'service': service,
                    'user': user,
                    'bucket': a
                }
                buckets_dict[server_id] = d

        for i in data:
            # Decimal to string
            i['total_original_amount'] = '{:f}'.format(i['total_original_amount'])
            i['total_trade_amount'] = '{:f}'.format(i['total_trade_amount'])

            bid = i['storage_bucket_id']
            if bid in buckets_dict:
                i.update(buckets_dict[bid])
            else:
                i['service'] = None
                i['bucket'] = None
                i['user'] = None

        return data

    def admin_aggregate_metering_by_user(
            self, user,
            date_start: date = None,
            date_end: date = None,
            user_id: str = None,
            service_id: str = None,
            order_by: str = None
    ):
        """
            管理员获取以 user 聚合的查询集
        """
        if user.is_federal_admin():
            queryset = self.filter_obs_metering_queryset(
                service_id=service_id, date_start=date_start, date_end=date_end, user_id=user_id, bucket_id=None
            )
            return self._aggregate_queryset_by_user(queryset, order_by=order_by)

        if service_id:
            service = ObjectsServiceManager.get_service_if_admin(user=user, service_id=service_id)
            if service is None:
                raise errors.AccessDenied(message=_('您没有指定服务的访问权限'))

        queryset = self.filter_obs_metering_queryset(
            service_id=service_id, date_start=date_start, date_end=date_end, user_id=user_id, bucket_id=None
        )

        if not service_id:
            qs = ObjectsServiceManager.get_all_has_perm_service(user)
            subq = Subquery(qs.values_list('id', flat=True))
            queryset = queryset.filter(service_id__in=subq)

        return self._aggregate_queryset_by_user(queryset, order_by=order_by)

    AGGREGATION_USER_ORDER_BY_CHOICES = [
        'total_original_amount', '-total_original_amount', 'total_storage_hours', '-total_storage_hours'
    ]

    @staticmethod
    def _aggregate_queryset_by_user(queryset, order_by: str):
        """
        按 user 聚合bucket计量数据
        """
        if not order_by:
            order_by = 'user_id'

        queryset = queryset.values('user_id').annotate(
            total_storage_hours=Sum('storage'),
            total_downstream=Sum('downstream'),
            total_get_request=Sum('get_request'),
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount'),
            bucket_count=Count('storage_bucket_id', distinct=True)
        ).order_by(order_by)

        return queryset

    @staticmethod
    def aggregate_by_user_mixin_data(data: list):
        """
        按 user 聚合数据分页后混合其他数据
        """
        user_ids = [i['user_id'] for i in data]
        users = UserProfile.objects.filter(
            id__in=user_ids).values('id', 'username', 'company')

        users_dict = {}
        for u in users:
            users_dict[u['id']] = {'username': u.get('username', ''), 'company': u.get('company', '')}

        for i in data:
            # Decimal to string
            i['total_original_amount'] = '{:f}'.format(i['total_original_amount'])
            i['total_trade_amount'] = '{:f}'.format(i['total_trade_amount'])

            uid = i['user_id']
            if uid in users_dict:
                i.update(users_dict[uid])
            else:
                i['username'] = ''
                i['company'] = ''

        return data

    def admin_aggregate_metering_by_service(
            self, user,
            date_start: date = None,
            date_end: date = None,
            service_id: str = None,
            order_by: str = None
    ):
        """
            管理员获取以 service 聚合的查询集
        """
        if user.is_federal_admin():
            queryset = self.filter_obs_metering_queryset(
                service_id=service_id, date_start=date_start, date_end=date_end, user_id=None, bucket_id=None
            )
            return self._aggregate_queryset_by_service(queryset, order_by=order_by)

        if service_id:
            service = ObjectsServiceManager.get_service_if_admin(user=user, service_id=service_id)
            if service is None:
                raise errors.AccessDenied(message=_('您没有指定服务的访问权限'))

        queryset = self.filter_obs_metering_queryset(
            service_id=service_id, date_start=date_start, date_end=date_end, user_id=None, bucket_id=None
        )

        if not service_id:
            qs = ObjectsServiceManager.get_all_has_perm_service(user)
            subq = Subquery(qs.values_list('id', flat=True))
            queryset = queryset.filter(service_id__in=subq)

        return self._aggregate_queryset_by_service(queryset, order_by=order_by)

    AGGREGATION_SERVICE_ORDER_BY_CHOICES = [
        'total_original_amount', '-total_original_amount', 'total_storage_hours', '-total_storage_hours'
    ]

    @staticmethod
    def _aggregate_queryset_by_service(queryset, order_by: str):
        """
        按 service 聚合bucket计量数据
        """
        if not order_by:
            order_by = 'service_id'

        queryset = queryset.values('service_id').annotate(
            total_storage_hours=Sum('storage'),
            total_downstream=Sum('downstream'),
            total_get_request=Sum('get_request'),
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount'),
            bucket_count=Count('storage_bucket_id', distinct=True),
            serving_user_count=Count('user_id', distinct=True)
        ).order_by(order_by)

        return queryset

    @staticmethod
    def aggregate_by_service_mixin_data(data: list):
        """
        按 service 聚合数据分页后混合其他数据
        """
        service_ids = [i['service_id'] for i in data]
        services = ObjectsService.objects.filter(id__in=service_ids).values('id', 'name')

        services_dict = {}
        for s in services:
            services_dict[s['id']] = s

        for i in data:
            # Decimal to string
            i['total_original_amount'] = '{:f}'.format(i['total_original_amount'])
            i['total_trade_amount'] = '{:f}'.format(i['total_trade_amount'])

            sid = i['service_id']
            if sid in services_dict:
                i['service'] = services_dict[sid]
            else:
                i['service'] = None

        return data

    def get_metering_statistics(self, service_id: str = None, date_start: date = None, date_end: date = None,):
        qs = self.filter_obs_metering_queryset(
            date_start=date_start, date_end=date_end, service_id=service_id
        )
        return qs.aggregate(
            total_storage_hours=Sum('storage'),
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount'),
        )


class StatementStorageManager:
    @staticmethod
    def get_statement_storage_queryset():
        return DailyStatementObjectStorage.objects.all()

    def filter_statement_storage_queryset(
            self, payment_status: str, date_start, date_end,
            user_id: str = None
    ):
        queryset = self.get_statement_storage_queryset()
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        if date_start:
            queryset = queryset.filter(date__gte=date_start)

        if date_end:
            queryset = queryset.filter(date__lte=date_end)

        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)

        return queryset.order_by('-creation_time')

    @staticmethod
    def get_statement_storage(statement_id: str, select_for_update: bool = False):
        if select_for_update:
            return DailyStatementObjectStorage.objects.filter(
                id=statement_id
            ).select_related('service').select_for_update().first()
        return DailyStatementObjectStorage.objects.filter(id=statement_id).select_related('service').first()

    def get_statement_storage_detail(
            self, statement_id: str, user, check_permission: bool = True
    ):
        statement = self.get_statement_storage(statement_id=statement_id)
        if statement is None:
            raise errors.TargetNotExist(message=_('指定编号的日结算单不存在'))

        if check_permission:
            if statement.user_id and statement.user_id != user.id:
                raise errors.AccessDenied(message=_('您没有权限访问该结算单'))

        return statement


class MeteringDiskManager(BaseMeteringManager):
    @staticmethod
    def get_metering_disk_queryset():
        return MeteringDisk.objects.all()

    @staticmethod
    def get_metering_by_id(metering_id: str) -> MeteringDisk:
        return MeteringDisk.objects.filter(id=metering_id).first()

    @staticmethod
    def get_metering(metering_id: str, user):
        """
        查询一个计量单，检查权限

        :raises: Error
        """
        metering = MeteringDiskManager.get_metering_by_id(metering_id=metering_id)
        if metering is None:
            raise errors.NotFound(message=_('计量单不存在。'))

        if metering.owner_type == metering.OwnerType.USER.value:
            if metering.user_id != user.id:
                raise errors.AccessDenied(message=_('无计量单的访问权限。'))
        elif metering.owner_type == metering.OwnerType.VO.value:
            VoManager().get_has_read_perm_vo(vo_id=metering.vo_id, user=user)

        return metering

    def filter_user_disk_metering(
            self, user,
            service_id: str = None,
            disk_id: str = None,
            date_start: date = None,
            date_end: date = None
    ):
        """
        查询用户云硬盘计量用量账单查询集
        """
        service_ids = [service_id] if service_id else None
        return self.filter_disk_metering_queryset(
            service_ids=service_ids, disk_id=disk_id, date_start=date_start,
            date_end=date_end, user_id=user.id
        )

    def filter_vo_disk_metering(
            self, user,
            vo_id: str,
            service_id: str = None,
            disk_id: str = None,
            date_start: date = None,
            date_end: date = None
    ):
        """
        查询vo组云硬盘计量用量账单查询集

        :rasies: AccessDenied, NotFound, Error
        """
        VoManager().get_has_read_perm_vo(vo_id=vo_id, user=user)
        service_ids = [service_id] if service_id else None
        return self.filter_disk_metering_queryset(
            service_ids=service_ids, disk_id=disk_id, date_start=date_start,
            date_end=date_end, vo_id=vo_id
        )

    def filter_disk_metering_by_admin(
            self, user,
            service_id: str = None,
            disk_id: str = None,
            date_start: date = None,
            date_end: date = None,
            vo_id: str = None,
            user_id: str = None
    ):
        """
        :rasies: AccessDenied, DiskNotExist, Error
        """
        if user.is_federal_admin():
            service_ids = [service_id] if service_id else None
            return self.filter_disk_metering_queryset(
                service_ids=service_ids, disk_id=disk_id, date_start=date_start, date_end=date_end,
                vo_id=vo_id, user_id=user_id
            )

        if disk_id:
            try:
                disk = DiskManager.get_disk_include_deleted(disk_id=disk_id)
            except errors.DiskNotExist:
                return MeteringDisk.objects.none()

            if service_id:
                if service_id != disk.service_id:
                    return MeteringDisk.objects.none()
            else:
                service_id = disk.service_id

        if service_id:
            service = ServiceManager.get_service_if_admin(user=user, service_id=service_id)
            if service is None:
                raise errors.AccessDenied(message=_('您没有指定服务的访问权限'))
            service_ids = [service_id]
        else:
            qs = ServiceManager.get_all_has_perm_service(user)
            service_ids = list(qs.values_list('id', flat=True))
            if not service_ids:
                return MeteringDisk.objects.none()

        queryset = self.filter_disk_metering_queryset(
            service_ids=service_ids, disk_id=disk_id, date_start=date_start, date_end=date_end,
            vo_id=vo_id, user_id=user_id
        )
        return queryset

    def filter_disk_metering_queryset(
            self, service_ids: list = None,
            disk_id: str = None,
            date_start: date = None,
            date_end: date = None,
            user_id: str = None,
            vo_id: str = None
    ):
        """
        查询云硬盘计量用量账单查询集
        """
        if user_id and vo_id:
            raise errors.Error(_('云硬盘计量用量账单查询集查询条件不能同时包含"user_id"和"vo_id"'))

        lookups = {}
        if date_start:
            lookups['date__gte'] = date_start

        if date_end:
            lookups['date__lte'] = date_end

        if service_ids:
            if len(service_ids) == 1:
                lookups['service_id'] = service_ids[0]
            else:
                lookups['service_id__in'] = service_ids

        if disk_id:
            lookups['disk_id'] = disk_id

        if user_id:
            lookups['owner_type'] = OwnerType.USER.value
            lookups['user_id'] = user_id

        if vo_id:
            lookups['owner_type'] = OwnerType.VO.value
            lookups['vo_id'] = vo_id

        queryset = self.get_metering_disk_queryset()
        return queryset.filter(**lookups).order_by('-creation_time')

    @staticmethod
    def get_meterings_by_statement_id(statement_id: str, _date: date):
        queryset = MeteringDiskManager.get_metering_disk_queryset()
        return queryset.filter(date=_date, daily_statement_id=statement_id)

    def admin_aggregate_metering_by_disk(
            self, user,
            date_start: date = None,
            date_end: date = None,
            user_id: str = None,
            service_id: str = None,
            vo_id: str = None
    ):
        """
        管理员获取以disk_id聚合的查询集
        """
        queryset = self.filter_disk_metering_by_admin(
            user=user, date_start=date_start, date_end=date_end, service_id=service_id, user_id=user_id, vo_id=vo_id
        )
        return self.aggregate_queryset_by_disk(queryset)

    def aggregate_user_metering_by_disk(
            self, user,
            date_start: date = None,
            date_end: date = None,
            service_id: str = None
    ):
        """
        普通用户获取自己名下以disk_id聚合的查询集
        """
        queryset = self.filter_user_disk_metering(
            user=user, date_start=date_start, date_end=date_end, service_id=service_id
        )
        return self.aggregate_queryset_by_disk(queryset)

    def aggregate_vo_metering_by_disk(
            self, user,
            date_start: date = None,
            date_end: date = None,
            service_id: str = None,
            vo_id: str = None
    ):
        """
        指定vo组下以disk_id聚合的查询集
        """
        queryset = self.filter_vo_disk_metering(
            user=user, vo_id=vo_id, service_id=service_id, date_start=date_start, date_end=date_end
        )
        return self.aggregate_queryset_by_disk(queryset)

    @staticmethod
    def aggregate_queryset_by_disk(queryset):
        """
        聚合云硬盘计量数据
        """
        queryset = queryset.values('disk_id').annotate(
            total_size_hours=Sum('size_hours'),
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount')
        ).order_by('disk_id')

        return queryset

    @staticmethod
    def aggregate_by_disk_mixin_data(data: list):
        """
        按disk id聚合数据分页后混合其他数据
        """
        disk_ids = [i['disk_id'] for i in data]
        disks = Disk.objects.filter(id__in=disk_ids).values(
            'id', 'size', 'remarks', 'pay_type', 'service_id', 'service__name')

        disk_dict = {}
        for disk in disks:
            disk_dict[disk['id']] = {
                'service_id': disk.pop('service_id', None),
                'service_name': disk.pop('service__name', None),
                'disk': disk
            }

        for i in data:
            d_id = i['disk_id']
            if d_id in disk_dict:
                i.update(disk_dict[d_id])
            else:
                i['service_id'] = ''
                i['service_name'] = ''
                i['disk'] = None

        return data

    def admin_aggregate_metering_by_user(
            self, user,
            date_start: date = None,
            date_end: date = None,
            service_id: str = None,
            order_by: str = None
    ):
        """
        管理员获取以user_id聚合的查询集
        """
        queryset = self.filter_disk_metering_by_admin(
            user=user, date_start=date_start, date_end=date_end, service_id=service_id
        )
        queryset = queryset.filter(owner_type=OwnerType.USER.value)
        return self.aggregate_queryset_by_user(queryset, order_by=order_by)

    @staticmethod
    def aggregate_queryset_by_user(queryset, order_by: str = None):
        """
        聚合用户的disk计量数据
        """
        if not order_by:
            order_by = 'user_id'

        queryset = queryset.values('user_id').annotate(
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount'),
            total_disk=Count('disk_id', distinct=True),
        ).order_by(order_by)

        return queryset

    def admin_aggregate_metering_by_vo(
            self, user,
            date_start: date = None,
            date_end: date = None,
            service_id: str = None,
            order_by: str = None
    ):
        """
        管理员获取以vo_id聚合的查询集
        """
        queryset = self.filter_disk_metering_by_admin(
            user=user, date_start=date_start, date_end=date_end, service_id=service_id
        ).filter(owner_type=OwnerType.VO.value)
        return self.aggregate_queryset_by_vo(queryset, order_by=order_by)

    @staticmethod
    def aggregate_queryset_by_vo(queryset, order_by: str = None):
        """
        聚合vo组的disk计量数据
        """
        if not order_by:
            order_by = 'vo_id'

        queryset = queryset.values('vo_id').annotate(
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount'),
            total_disk=Count('disk_id', distinct=True),
        ).order_by(order_by)

        return queryset

    def admin_aggregate_metering_by_service(
            self, user,
            date_start: date = None,
            date_end: date = None,
            order_by: str = None
    ):
        """
        管理员获取以service_id聚合的查询集
        """
        queryset = self.filter_disk_metering_by_admin(
            user=user, date_start=date_start, date_end=date_end
        )
        return self.aggregate_queryset_by_service(queryset, order_by=order_by)

    @staticmethod
    def aggregate_queryset_by_service(queryset, order_by: str = None):
        """
        聚合服务节点的云主机计量数据
        """
        if not order_by:
            order_by = 'service_id'

        queryset = queryset.values('service_id').annotate(
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount'),
            total_disk=Count('disk_id', distinct=True),
        ).order_by(order_by)

        return queryset


class StatementDiskManager(BaseStatementManager):
    @staticmethod
    def get_statement_disk_queryset():
        return DailyStatementDisk.objects.all()

    def filter_statement_disk_queryset(
            self, payment_status: str, date_start, date_end,
            user_id: str = None, vo_id: str = None
    ):
        """
        查询用户或vo组的日结算单查询集
        """
        queryset = self.get_statement_disk_queryset()
        return self.filter_statement_queryset(
            queryset=queryset, payment_status=payment_status, date_start=date_start, date_end=date_end,
            user_id=user_id, vo_id=vo_id
        )

    def filter_vo_statement_disk_queryset(
        self, payment_status: str, date_start, date_end, user, vo_id: str
    ):
        """
        查询vo组的日结算单查询集

        :raises: AccessDenied
        """
        self.has_vo_permission(vo_id=vo_id, user=user)
        return self.filter_statement_disk_queryset(
            payment_status=payment_status, date_start=date_start,
            date_end=date_end, vo_id=vo_id
        )

    @staticmethod
    def get_statement_disk(statement_id: str, select_for_update: bool = False):
        if select_for_update:
            return DailyStatementDisk.objects.filter(
                id=statement_id
            ).select_related('service').select_for_update().first()

        return DailyStatementDisk.objects.filter(id=statement_id).select_related('service').first()

    def get_statement_disk_detail(
            self, statement_id: str, user, check_permission: bool = True, read_only: bool = True
    ):
        """
        查询日结算单详情

        :param check_permission: 是否检测权限
        :param read_only: 用于vo组权限检测；True：只需要访问权限；False: 需要管理权限
        :return:
            statement_server
        """
        statement = self.get_statement_disk(statement_id=statement_id)
        if statement is None:
            raise errors.NotFound(_('日结算单不存在'))

        # check permission
        if check_permission:
            if statement.owner_type == OwnerType.USER.value:
                if statement.user_id and statement.user_id != user.id:
                    raise errors.AccessDenied(message=_('您没有此日结算单访问权限'))
            elif statement.vo_id:
                self.has_vo_permission(vo_id=statement.vo_id, user=user, read_only=read_only)

        return statement


class MeteringMonitorSiteManager:
    @staticmethod
    def get_metering_queryset():
        return MeteringMonitorWebsite.objects.all()

    def filter_user_metering(
            self, user_id: str,
            site_id: str = None,
            date_start: date = None,
            date_end: date = None
    ):
        """
        查询用户的站点监控的计量账单的查询集合
        """
        return self.filter_metering_queryset(
            site_id=site_id, date_start=date_start, date_end=date_end, user_id=user_id
        )

    def filter_metering_by_admin(
            self, admin_user,
            site_id: str = None,
            date_start: date = None,
            date_end: date = None,
            user_id: str = None
    ):
        """
        查询用户的站点监控的计量账单的查询集合
        :return: QuerySet()
        :raises: Error
        """
        if admin_user.is_federal_admin():
            return self.filter_metering_queryset(
                site_id=site_id, date_start=date_start, date_end=date_end, user_id=user_id
            )

        raise errors.AccessDenied(message=_('您没有管理员权限'))

    def filter_metering_queryset(
            self,
            site_id: str = None,
            date_start: date = None,
            date_end: date = None,
            user_id: str = None
    ):
        lookups = {}
        if user_id:
            lookups['user_id'] = user_id

        if site_id:
            lookups['website_id'] = site_id

        if date_start:
            lookups['date__gte'] = date_start

        if date_end:
            lookups['date__lte'] = date_end

        queryset = self.get_metering_queryset()
        return queryset.filter(**lookups).order_by('-creation_time')

    @staticmethod
    def get_meterings_by_statement_id(statement_id: str, _date: date):
        return MeteringMonitorWebsite.objects.filter(date=_date, daily_statement_id=statement_id)

    @staticmethod
    def get_statement_queryset():
        return DailyStatementMonitorWebsite.objects.all()

    def filter_statement_queryset(
            self, payment_status: str, date_start, date_end,
            user_id: str = None
    ):
        queryset = self.get_statement_queryset()
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        if date_start:
            queryset = queryset.filter(date__gte=date_start)

        if date_end:
            queryset = queryset.filter(date__lte=date_end)

        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)

        return queryset.order_by('-creation_time')

    @staticmethod
    def get_site_statement(statement_id: str, select_for_update: bool = False):
        if select_for_update:
            return DailyStatementMonitorWebsite.objects.filter(
                id=statement_id
            ).select_for_update().first()

        return DailyStatementMonitorWebsite.objects.filter(id=statement_id).first()

    def get_site_statement_detail(
            self, statement_id: str, user, check_permission: bool = True
    ):
        statement = self.get_site_statement(statement_id=statement_id)
        if statement is None:
            raise errors.TargetNotExist(message=_('指定编号的日结算单不存在'))

        if check_permission:
            if statement.user_id and statement.user_id != user.id:
                raise errors.AccessDenied(message=_('您没有权限访问该日结算单'))

        return statement
