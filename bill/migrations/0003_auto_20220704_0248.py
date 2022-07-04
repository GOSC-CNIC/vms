# Generated by Django 3.2.13 on 2022-07-04 02:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('service', '0003_serviceconfig_pay_app_service_id'),
        ('bill', '0002_auto_20220622_0835'),
    ]

    operations = [
        migrations.AddField(
            model_name='payappservice',
            name='category',
            field=models.CharField(choices=[('vms-server', 'VMS云服务器'), ('vms-object', 'VMS对象存储'), ('high-cloud', '高等级云'), ('hpc', '高性能计算'), ('other', '其他')], default='other', max_length=16, verbose_name='服务类别'),
        ),
        migrations.AddField(
            model_name='payappservice',
            name='service',
            field=models.OneToOneField(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='service.serviceconfig', verbose_name='对应的VMS服务'),
        ),
    ]
