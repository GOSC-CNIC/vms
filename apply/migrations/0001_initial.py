# Generated by Django 4.2.9 on 2024-03-12 03:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('service', '0010_remove_datacenter_endpoint_compute_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CouponApply',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_type', models.CharField(choices=[('server', '云主机'), ('storage', '对象存储'), ('monitor-site', '站点监控'), ('scan', '安全扫描')], max_length=16, verbose_name='服务类型')),
                ('service_id', models.CharField(max_length=36, verbose_name='服务单元id')),
                ('service_name', models.CharField(max_length=255, verbose_name='服务单元名称')),
                ('service_name_en', models.CharField(max_length=255, verbose_name='服务单元英文名称')),
                ('pay_service_id', models.CharField(max_length=36, verbose_name='钱包结算单元id')),
                ('face_value', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='申请面额')),
                ('expiration_time', models.DateTimeField(verbose_name='过期时间')),
                ('apply_desc', models.CharField(max_length=255, verbose_name='申请描述')),
                ('creation_time', models.DateTimeField(verbose_name='创建时间')),
                ('update_time', models.DateTimeField(verbose_name='更新时间')),
                ('user_id', models.CharField(max_length=36, verbose_name='申请人id')),
                ('username', models.CharField(max_length=128, verbose_name='申请人')),
                ('vo_id', models.CharField(blank=True, default='', max_length=36, verbose_name='项目组id')),
                ('vo_name', models.CharField(blank=True, default='', max_length=128, verbose_name='项目组名称')),
                ('owner_type', models.CharField(choices=[('user', '用户'), ('vo', 'VO组')], max_length=16, verbose_name='所属类型')),
                ('status', models.CharField(choices=[('wait', '待审批'), ('cancel', '取消'), ('pending', '审批中'), ('reject', '拒绝'), ('pass', '通过')], default='wait', max_length=16, verbose_name='状态')),
                ('approver', models.CharField(blank=True, default='', max_length=128, verbose_name='审批人')),
                ('reject_reason', models.CharField(blank=True, default='', max_length=255, verbose_name='拒绝原因')),
                ('approved_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='审批通过金额')),
                ('coupon_id', models.CharField(blank=True, default='', max_length=36, verbose_name='资源券id')),
                ('deleted', models.BooleanField(default=False, verbose_name='删除')),
                ('delete_user', models.CharField(blank=True, default='', max_length=128, verbose_name='删除人')),
                ('odc', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='service.orgdatacenter', verbose_name='数据中心')),
            ],
            options={
                'verbose_name': '资源券申请',
                'verbose_name_plural': '资源券申请',
                'db_table': 'apply_coupon',
                'ordering': ['-creation_time'],
                'indexes': [models.Index(fields=['user_id'], name='idx_user_id'), models.Index(fields=['vo_id'], name='idx_vo_id')],
            },
        ),
    ]
