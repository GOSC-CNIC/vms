# Generated by Django 3.2.5 on 2021-09-07 08:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('service', '0005_applyquota_result_desc'),
    ]

    operations = [
        migrations.CreateModel(
            name='MonitorProvider',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=255, verbose_name='监控服务名称')),
                ('name_en', models.CharField(default='', max_length=255, verbose_name='监控服务名称')),
                ('endpoint_url', models.CharField(default='', help_text='http(s)://example.cn/', max_length=255, verbose_name='服务url地址')),
                ('username', models.CharField(blank=True, default='', help_text='用于此服务认证的用户名', max_length=128, verbose_name='认证用户名')),
                ('password', models.CharField(blank=True, default='', max_length=255, verbose_name='认证密码')),
                ('creation', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
            ],
            options={
                'verbose_name': '监控服务配置信息',
                'verbose_name_plural': '监控服务配置信息',
                'ordering': ['-creation'],
            },
        ),
        migrations.CreateModel(
            name='MonitorJobCeph',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=255, verbose_name='监控的CEPH集群名称')),
                ('name_en', models.CharField(default='', max_length=255, verbose_name='监控的CEPH集群英文名称')),
                ('job_tag', models.CharField(default='', max_length=255, verbose_name='CEPH集群标签名称')),
                ('creation', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='monitor.monitorprovider', verbose_name='监控服务配置')),
                ('service', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='monitor_job_ceph_set', to='service.serviceconfig', verbose_name='所属的服务')),
            ],
            options={
                'verbose_name': '监控任务节点',
                'verbose_name_plural': '监控任务节点',
                'ordering': ['-creation'],
            },
        ),
    ]
