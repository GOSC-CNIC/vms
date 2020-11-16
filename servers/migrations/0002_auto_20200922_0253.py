# Generated by Django 2.2.16 on 2020-09-22 02:53

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('service', '0002_auto_20200922_0253'),
        ('servers', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Flavor',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID')),
                ('vcpus', models.IntegerField(default=0, verbose_name='虚拟CPU数')),
                ('ram', models.IntegerField(default=0, verbose_name='内存MB')),
                ('enable', models.BooleanField(default=True, verbose_name='可用状态')),
                ('creation_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
            ],
            options={
                'verbose_name': '配置样式',
                'verbose_name_plural': '配置样式',
                'db_table': 'flavor',
                'ordering': ['-id'],
            },
        ),
        migrations.RemoveField(
            model_name='server',
            name='deleted',
        ),
        migrations.AddField(
            model_name='server',
            name='public_ip',
            field=models.BooleanField(default=True, verbose_name='公/私网'),
        ),
        migrations.AlterField(
            model_name='server',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='user_servers', to=settings.AUTH_USER_MODEL, verbose_name='创建者'),
        ),
        migrations.CreateModel(
            name='ServerArchive',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='服务器实例名称')),
                ('instance_id', models.CharField(help_text='各接入服务中虚拟主机的ID', max_length=128, verbose_name='虚拟主机ID')),
                ('vcpus', models.IntegerField(default=0, verbose_name='虚拟CPU数')),
                ('ram', models.IntegerField(default=0, verbose_name='内存MB')),
                ('ipv4', models.CharField(default='', max_length=128, verbose_name='IPV4')),
                ('public_ip', models.BooleanField(default=True, verbose_name='公/私网')),
                ('image_id', models.CharField(default='', max_length=128, verbose_name='镜像ID')),
                ('image', models.CharField(default='', max_length=255, verbose_name='镜像系统名称')),
                ('creation_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('remarks', models.CharField(blank=True, default='', max_length=255, verbose_name='备注')),
                ('deleted_time', models.DateTimeField(auto_now_add=True, verbose_name='删除归档时间')),
                ('service', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='server_archive_set', to='service.ServiceConfig', verbose_name='接入的服务配置')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='user_server_archives', to=settings.AUTH_USER_MODEL, verbose_name='创建者')),
            ],
            options={
                'verbose_name': '服务器归档记录',
                'verbose_name_plural': '服务器归档记录',
                'ordering': ['-id'],
            },
        ),
    ]
