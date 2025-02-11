import datetime

from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core import errors
from apps.api.viewsets import NormalGenericViewSet
from apps.api.paginations import NewPageNumberPagination100
from apps.app_report import serializers as report_serializers
from apps.app_report.managers import BktStatsMonthQueryOrderBy, BucketStatsMonthlyManager, StorageAggQueryOrderBy
from utils.paginators import NoPaginatorInspector


class BucketStatsMonthlyViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举存储桶容量与计费金额月度统计数据'),
        manual_parameters=[
            openapi.Parameter(
                name='date_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('起始年月，格式：YYYY-MM')
            ),
            openapi.Parameter(
                name='date_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('截止年月，格式：YYYY-MM')
            ),
            openapi.Parameter(
                name='order_by',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'排序方式，默认按创建时间降序，{BktStatsMonthQueryOrderBy.choices}'
            ),
            openapi.Parameter(
                name='bucket_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='查询指定存储桶'
            )
        ] + NormalGenericViewSet.PARAMETERS_AS_ADMIN,
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举存储桶容量与计费金额月度统计数据，查询个人的，或以联邦管理员身份查询所有的

            http code 200：
            {
              "count": 762,
              "page_num": 1,
              "page_size": 100,
              "results": [
                {
                  "id": "bb4u5dip0vmeh5f2ahors2vcq",
                  "service": {
                    "id": "0fb92e48-3565-11ed-9877-c8009fe2eb03",
                    "name": "中国科技云对象存储服务",
                    "name_en": "CSTCloud Object Storage"
                  },
                  "bucket_id": "34e76f20-6965-11ed-9d25-c8009fe2eb03",
                  "bucket_name": "fast-obs",
                  "size_byte": 1854680422194811,    # 桶总容量
                  "increment_byte": 0,              # 本月容量增量
                  "object_count": 3996327,          # 对象数量
                  "original_amount": "201644.19",   # 本月计量金额
                  "increment_amount": "201644.19",  # 本月计量金额增量
                  "user_id": "1795e1e6-35f8-11ec-86db-c8009fe2eb03",
                  "username": "tom@cnic.cn",
                  "date": "2023-07",
                  "creation_time": "2023-09-06T06:55:35.581415Z"
                }
              ]
            }
        """
        date_start = request.query_params.get('date_start', None)
        date_end = request.query_params.get('date_end', None)
        order_by = request.query_params.get('order_by', None)
        bucket_id = request.query_params.get('bucket_id', None)

        try:
            if date_start is not None:
                try:
                    date_start = datetime.date.fromisoformat(date_start + '-01')
                except (TypeError, ValueError):
                    raise errors.InvalidArgument(message=_('起始日期格式无效'))

            if date_end is not None:
                try:
                    date_end = datetime.date.fromisoformat(date_end + '-01')
                except (TypeError, ValueError):
                    raise errors.InvalidArgument(message=_('截止日期格式无效'))

            if date_start and date_end:
                if date_start > date_end:
                    raise errors.InvalidArgument(message=_('起始日期不能在截止日期之前'))

            if order_by is not None:
                if order_by not in BktStatsMonthQueryOrderBy.values:
                    raise errors.InvalidArgument(message=_('指定的排序方式无效'), code='InvalidOrderBy')
            else:
                order_by = BktStatsMonthQueryOrderBy.CREATION_TIME_DESC.value
        except Exception as exc:
            return self.exception_response(exc)

        user = request.user
        if self.is_as_admin_request(request):
            if not user.is_federal_admin():
                return self.exception_response(exc=errors.AccessDenied(message=_('你没有联邦管理员权限')))

            qs = BucketStatsMonthlyManager().admin_bkt_stats_queryset(
                date_start=date_start, date_end=date_end, order_by=order_by, bucket_id=bucket_id
            )
        else:
            qs = BucketStatsMonthlyManager().get_user_bkt_stats_queryset(
                user_id=user.id, date_start=date_start, date_end=date_end, order_by=order_by, bucket_id=bucket_id
            )

        try:
            services = self.paginate_queryset(queryset=qs)
            serializer = self.get_serializer(services, many=True)
            return self.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return self.exception_response(exc)

    def get_serializer_class(self):
        if self.action == 'list':
            return report_serializers.BucketStatsMonthlySerializer

        return Serializer


class StorageStatsMonthlyViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举对象存储容量与计费金额月度统计数据'),
        paginator_inspectors=[NoPaginatorInspector],
        manual_parameters=[
            openapi.Parameter(
                name='date_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('起始年月，格式：YYYY-MM')
            ),
            openapi.Parameter(
                name='date_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('截止年月，格式：YYYY-MM')
            ),
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='查询指定存储服务单元'
            )
        ] + NormalGenericViewSet.PARAMETERS_AS_ADMIN,
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举对象存储容量与计费金额月度统计数据，以联邦管理员身份查询

            http code 200：
            {
              "results": [
                {
                  "date": "2023-08",
                  "total_size_byte": 1234456789,
                  "total_increment_byte": 10,
                  "total_original_amount": 0.72,
                  "total_increment_amount": 0.12
                }
              ]
            }
        """
        date_start = request.query_params.get('date_start', None)
        date_end = request.query_params.get('date_end', None)
        service_id = request.query_params.get('service_id', None)

        try:
            if date_start is not None:
                try:
                    date_start = datetime.date.fromisoformat(date_start + '-01')
                except (TypeError, ValueError):
                    raise errors.InvalidArgument(message=_('起始日期格式无效'))

            if date_end is not None:
                try:
                    date_end = datetime.date.fromisoformat(date_end + '-01')
                except (TypeError, ValueError):
                    raise errors.InvalidArgument(message=_('截止日期格式无效'))

            if date_start and date_end:
                if date_start > date_end:
                    raise errors.InvalidArgument(message=_('起始日期不能在截止日期之前'))
        except Exception as exc:
            return self.exception_response(exc)

        service_ids = [service_id] if service_id else None
        user = request.user
        if self.is_as_admin_request(request):
            if not user.is_federal_admin():
                return self.exception_response(exc=errors.AccessDenied(message=_('你没有联邦管理员权限')))

            qs = BucketStatsMonthlyManager().admin_aggregate_storage_stats_by_date(
                date_start=date_start, date_end=date_end, service_ids=service_ids
            )
        else:
            qs = BucketStatsMonthlyManager().user_aggregate_storage_stats_by_date(
                user_id=user.id, date_start=date_start, date_end=date_end, service_ids=service_ids
            )

        try:
            data = []
            for item in qs:
                dt = item['date']
                item['date'] = f"{dt.year:04}-{dt.month:02}"
                data.append(item)

            return Response(data={'results': data})
        except Exception as exc:
            return self.exception_response(exc)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举指定月份各服务单元的对象存储容量与计费金额月度统计数据'),
        paginator_inspectors=[NoPaginatorInspector],
        manual_parameters=[
            openapi.Parameter(
                name='date',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=gettext_lazy('年月，格式：YYYY-MM')
            ),
            openapi.Parameter(
                name='order_by',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'排序方式，默认按创建时间降序，{StorageAggQueryOrderBy.choices}'
            ),
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['GET'], detail=False, url_path='service', url_name='service')
    def agg_by_service(self, request, *args, **kwargs):
        """
        列举指定月份各服务单元的对象存储容量与计费金额月度统计数据，以联邦管理员身份查询

            http code 200：
            {
              "date": "2023-08",
              "results": [
                {
                  "service": {
                    "id": "xxx",
                    "name": "xxx",
                    "name_en": "xxx"
                  },
                  "service_id": "xxx",
                  "total_size_byte": 1234456789,    # 存储总容量
                  "total_increment_byte": 10,       # 本月总容量增量
                  "total_original_amount": 0.72,    # 本月总计量金额
                  "total_increment_amount": 0.12    # 本月总计量金额增量
                }
              ]
            }
        """
        query_date = request.query_params.get('date', None)
        order_by = request.query_params.get('order_by', None)

        try:
            if query_date is None:
                raise errors.InvalidArgument(message=_('必须指定查询年月'))

            try:
                query_date = datetime.date.fromisoformat(query_date + '-01')
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('指定查询年月格式无效'))

            if order_by is not None:
                if order_by not in StorageAggQueryOrderBy.values:
                    raise errors.InvalidArgument(message=_('指定的排序方式无效'), code='InvalidOrderBy')
        except Exception as exc:
            return self.exception_response(exc)

        user = request.user
        if not user.is_federal_admin():
            return self.exception_response(exc=errors.AccessDenied(message=_('你没有联邦管理员权限')))

        qs = BucketStatsMonthlyManager().admin_aggregate_storage_by_service(
            _date=query_date, service_ids=None, order_by=order_by
        )

        try:
            ym = f"{query_date.year:04}-{query_date.month:02}"
            data = BucketStatsMonthlyManager.agg_by_service_mixin_data(data=list(qs))
            return Response(data={'date': ym, 'results': data})
        except Exception as exc:
            return self.exception_response(exc)

    def get_serializer_class(self):
        return Serializer
