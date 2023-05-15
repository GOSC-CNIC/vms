from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django import forms

from utils.model import NoDeleteSelectModelAdmin
from .models import Server, Flavor, ServerArchive


class ServerAdminForm(forms.ModelForm):
    change_password = forms.CharField(
        label=_('更改默认登录密码输入'), required=False, min_length=3, max_length=32,
        help_text=_('如果要更改默认登录密码，请在此输入新密码, 不修改请保持为空'))

    def save(self, commit=True):
        change_password = self.cleaned_data.get('change_password')      # 如果输入新密码则更改
        if change_password:
            self.instance.raw_default_password = change_password

        return super().save(commit=commit)


@admin.register(Server)
class ServerAdmin(NoDeleteSelectModelAdmin):
    form = ServerAdminForm
    list_display_links = ('id',)
    list_display = ('id', 'service', 'azone_id', 'instance_id', 'vcpus', 'ram', 'disk_size', 'ipv4', 'image',
                    'creation_time', 'start_time', 'user', 'task_status', 'center_quota',
                    'pay_type', 'classification', 'vo', 'lock', 'situation', 'situation_time',
                    'default_user', 'show_default_password', 'expiration_time', 'remarks')
    search_fields = ['id', 'name', 'image', 'ipv4', 'remarks']
    list_filter = ['service__data_center', 'service', 'classification']
    raw_id_fields = ('user', )
    list_select_related = ('service', 'user', 'vo')
    readonly_fields = ['default_password']

    fieldsets = [
        (_('基础信息'), {'fields': ('service', 'azone_id', 'instance_id', 'remarks', 'center_quota')}),
        (_('配置信息'), {'fields': ('vcpus', 'ram', 'disk_size', 'ipv4', 'image')}),
        (_('默认登录密码'), {'fields': ('default_user', 'default_password', 'change_password')}),
        (_('创建和归属信息'), {'fields': ('creation_time', 'task_status', 'classification', 'user', 'vo')}),
        (_('计量和管控信息'), {'fields': (
            'pay_type', 'start_time', 'expiration_time', 'lock', 'situation', 'situation_time')}),
    ]

    @admin.display(
        description=_('默认登录密码')
    )
    def show_default_password(self, obj):
        return obj.raw_default_password

    def has_delete_permission(self, request, obj=None):
        return False

    def delete_model(self, request, obj):
        """
        Given a model instance delete it from the database.
        """
        raise Exception(_('不允许从后台删除。'))


@admin.register(ServerArchive)
class ServerArchiveAdmin(NoDeleteSelectModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'name', 'instance_id', 'vcpus', 'ram', 'disk_size', 'ipv4', 'image',
                    'creation_time', 'user', 'task_status', 'pay_type', 'classification', 'vo',
                    'center_quota',
                    'start_time', 'deleted_time', 'archive_user', 'archive_type', 'remarks')
    search_fields = ['id', 'name', 'image', 'ipv4', 'remarks']
    list_filter = ['service', 'classification']
    raw_id_fields = ('user',)
    list_select_related = ('service', 'user', 'archive_user', 'vo')
    show_full_result_count = False


@admin.register(Flavor)
class FlavorAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'vcpus', 'ram', 'enable', 'service', 'creation_time')
    ordering = ('vcpus', 'ram')
    list_filter = ['service']
