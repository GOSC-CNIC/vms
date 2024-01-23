# Generated by Django 4.2.7 on 2023-11-29 02:23

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import netbox.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ipam', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='IPv6RangeRecord',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_time', models.DateTimeField(verbose_name='创建时间')),
                ('record_type', models.CharField(choices=[('assign', '分配'), ('recover', '收回'), ('split', '拆分'), ('merge', '合并'), ('add', '添加'), ('change', '修改'), ('delete', '删除'), ('reserve', '预留')], max_length=16, verbose_name='记录类型')),
                ('ip_ranges', models.JSONField(blank=True, default=dict, verbose_name='拆分或合并的IP段')),
                ('remark', models.CharField(blank=True, default='', max_length=255, verbose_name='备注信息')),
                ('start_address', netbox.fields.ByteField(max_length=16, verbose_name='起始地址')),
                ('end_address', netbox.fields.ByteField(max_length=16, verbose_name='截止地址')),
                ('prefixlen', models.PositiveIntegerField(validators=[django.core.validators.MaxValueValidator(128)], verbose_name='前缀长度')),
                ('org_virt_obj', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='ipam.orgvirtualobject', verbose_name='分配给机构虚拟对象')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='操作用户')),
            ],
            options={
                'verbose_name': 'IPv6段操作记录',
                'verbose_name_plural': 'IPv6段操作记录',
                'db_table': 'ipam_ipv6_range_record',
                'ordering': ('-creation_time',),
            },
        ),
        migrations.CreateModel(
            name='IPv6Range',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, default='', max_length=255, verbose_name='名称')),
                ('status', models.CharField(choices=[('assigned', '已分配'), ('reserved', '预留'), ('wait', '未分配')], default='wait', max_length=16, verbose_name='状态')),
                ('creation_time', models.DateTimeField(verbose_name='创建时间')),
                ('update_time', models.DateTimeField(verbose_name='更新时间')),
                ('assigned_time', models.DateTimeField(blank=True, default=None, null=True, verbose_name='分配时间')),
                ('admin_remark', models.CharField(blank=True, default='', max_length=255, verbose_name='科技网管理员备注信息')),
                ('remark', models.CharField(blank=True, default='', max_length=255, verbose_name='机构管理员备注信息')),
                ('start_address', netbox.fields.ByteField(max_length=16, verbose_name='起始地址')),
                ('end_address', netbox.fields.ByteField(max_length=16, verbose_name='截止地址')),
                ('prefixlen', models.PositiveIntegerField(validators=[django.core.validators.MaxValueValidator(128)], verbose_name='前缀长度')),
                ('asn', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='ipam.asn', verbose_name='AS编号')),
                ('org_virt_obj', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='ipam.orgvirtualobject', verbose_name='分配给机构二级')),
            ],
            options={
                'verbose_name': 'IPv6地址段',
                'verbose_name_plural': 'IPv6地址段',
                'db_table': 'ipam_ipv6_range',
                'ordering': ('start_address',),
            },
        ),
        migrations.CreateModel(
            name='IPv6Address',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_time', models.DateTimeField(verbose_name='创建时间')),
                ('update_time', models.DateTimeField(verbose_name='更新时间')),
                ('admin_remark', models.CharField(blank=True, default='', max_length=255, verbose_name='科技网管理员备注信息')),
                ('remark', models.CharField(blank=True, default='', max_length=255, verbose_name='机构管理员备注信息')),
                ('ip_address', netbox.fields.ByteField(max_length=16, verbose_name='IP地址')),
            ],
            options={
                'verbose_name': 'IPv6地址',
                'verbose_name_plural': 'IPv6地址',
                'db_table': 'ipam_ipv6_addr',
                'ordering': ('ip_address',),
            },
        ),
        migrations.AddIndex(
            model_name='ipv6range',
            index=models.Index(fields=['start_address'], name='idx_start_address'),
        ),
        migrations.AddIndex(
            model_name='ipv6range',
            index=models.Index(fields=['end_address'], name='idx_end_address'),
        ),
        migrations.AddConstraint(
            model_name='ipv6address',
            constraint=models.UniqueConstraint(fields=('ip_address',), name='unique_ipv6_address'),
        ),
    ]
