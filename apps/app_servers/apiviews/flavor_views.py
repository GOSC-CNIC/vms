from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.serializers import Serializer
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.app_servers import serializers as server_serializers
from apps.app_servers.handlers.flavor_handler import FlavorHandler
from apps.api.viewsets import CustomGenericViewSet
from apps.api.paginations import NewPageNumberPagination100


class FlavorViewSet(CustomGenericViewSet):
    """
    Flavor相关API
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = None

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举配置样式flavor'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='云主机服务单元id'
            ),
        ],
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举配置样式flavor

            Http Code: 状态码200，返回数据：
            {
              "flavors": [
                {
                  "id": 9c70cbe2-690c-11eb-a4b7-c8009fe2eb10,
                  "flavor_id": "ecs.s3.medium"
                  "vcpus": 4,
                  "ram": 4,      # GiB
                  "disk": 17
                  "service_id": "xxx",
                  "ram_gib": 4      # Gib
                }
              ]
            }
        """
        return FlavorHandler.list_flavors(view=self, request=request, kwargs=kwargs)


class AdminFlavorViewSet(CustomGenericViewSet):
    """
    Flavor相关API
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员创建云主机配置样式'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='云主机服务单元id'
            ),
        ],
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        为指定服务单元创建云主机配置样式，需要有服务单元管理权限

            Http Code: 状态码200，返回数据：
            {
                  "id": 9c70cbe2-690c-11eb-a4b7-c8009fe2eb10,
                  "service_id": "xxx",
                  "vcpus": 4,
                  "ram": 4,      # GiB
                  "enable": true    # true:启用；false：未启用
                  "disk": 17    # 特殊字段，未使用
                  "flavor_id": "ecs.s3.medium"  # 特殊字段，未使用
            }
        """
        return FlavorHandler.admin_create_flavor(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员列举云主机配置样式'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='云主机服务单元id'
            ),
            openapi.Parameter(
                name='enable',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description='启用状态筛选，true筛选启用的，false筛选未启用的，不提交不筛选'
            ),
        ],
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        管理员列举配置样式

            Http Code: 状态码200，返回数据：
            {
              "count": 9,
              "page_num": 1,
              "page_size": 100,
              "results": [
                {
                  "id": 9c70cbe2-690c-11eb-a4b7-c8009fe2eb10,
                  "service_id": "xxx",
                  "vcpus": 4,
                  "ram": 4,      # GiB
                  "enable": true    # true:启用；false：未启用
                  "disk": 17    # 特殊字段，未使用
                  "flavor_id": "ecs.s3.medium"  # 特殊字段，未使用
                }
              ]
            }
        """
        return FlavorHandler.admin_list_flavors(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员修改云主机配置样式'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['post'], detail=True, url_path='update', url_name='update')
    def update_flavor(self, request, *args, **kwargs):
        """
        管理员修改云主机配置样式，需要有服务单元管理权限

            Http Code: 状态码200，返回数据：
            {
                  "id": 9c70cbe2-690c-11eb-a4b7-c8009fe2eb10,
                  "service_id": "xxx",
                  "vcpus": 4,
                  "ram": 4,      # GiB
                  "enable": true    # true:启用；false：未启用
                  "disk": 17    # 特殊字段，未使用
                  "flavor_id": "ecs.s3.medium"  # 特殊字段，未使用
            }
        """
        return FlavorHandler.admin_update_flavor(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员删除云主机配置样式'),
        responses={
            204: ''
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        管理员删除云主机配置样式，需要有服务单元管理权限

            Http Code: 状态码204
        """
        return FlavorHandler.admin_delete_flavor(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return server_serializers.FlavorSerializer
        elif self.action in ['create', 'update_flavor']:
            return server_serializers.FlavorCreateSerializer

        return Serializer
