from django.contrib import admin
from apps.app_alert.models import AlertWhiteListModel
from apps.app_alert.models import AlertMonitorJobServer
from apps.app_alert.models import ScriptFlagModel
from utils.model import BaseModelAdmin


# Register your models here.
@admin.register(AlertWhiteListModel)
class AlertWhiteListAdmin(BaseModelAdmin):
    list_display = [
        'id',
        'ip',
        'remark',
        'creation',
        'modification', ]
    list_display_links = (
        'id',
        'ip',
        'remark',
        'creation',
        'modification',)


@admin.register(AlertMonitorJobServer)
class AlertMonitorJobServerAdmin(BaseModelAdmin):
    list_display = [
        'id',
        'name',
        'sort_weight',
        'remark', ]
    list_display_links = (
        'id',
        'name',
        'sort_weight',
        'remark',)

    filter_horizontal = (
        "users",
    )


@admin.register(ScriptFlagModel)
class ScriptFlagAdmin(BaseModelAdmin):
    list_display = [
        'id',
        'name',
        'start',
        'end',
        'status',
    ]
    list_display_links = (
        'id',
        'name',
        'start',
        'end',
        'status',
    )
