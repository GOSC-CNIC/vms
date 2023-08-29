# Generated by Django 4.2.4 on 2023-08-29 08:00

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BucketMonthlyReport',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_time', models.DateTimeField(verbose_name='生成时间')),
                ('report_date', models.DateField(help_text='报表月度，用日期存储年和月，日统一为1', verbose_name='报表年月')),
                ('username', models.CharField(blank=True, default='', max_length=128, verbose_name='用户名')),
                ('service_id', models.CharField(max_length=36, verbose_name='所属服务单元')),
                ('service_name', models.CharField(max_length=255, verbose_name='服务名称')),
                ('bucket_id', models.CharField(default='', help_text='对象存储中间件存储桶实例id', max_length=36, verbose_name='存储桶实例ID')),
                ('bucket_name', models.CharField(max_length=63, verbose_name='存储桶名称')),
                ('storage_days', models.FloatField(blank=True, default=0, help_text='存储桶的存储容量GiB天数', verbose_name='存储容量GiB*Day')),
                ('original_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='计费金额')),
                ('payable_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='按量应付金额')),
            ],
            options={
                'verbose_name': '存储桶月度计量报表',
                'verbose_name_plural': '存储桶月度计量报表',
                'db_table': 'monthly_bucket_metering',
                'ordering': ['-creation_time'],
            },
        ),
        migrations.CreateModel(
            name='MonthlyReport',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_time', models.DateTimeField(verbose_name='生成时间')),
                ('report_date', models.DateField(help_text='报表月度，用日期存储年和月，日统一为1', verbose_name='报表年月')),
                ('period_start_time', models.DateTimeField(default=None, null=True, verbose_name='月度报表周期开始时间')),
                ('period_end_time', models.DateTimeField(default=None, null=True, verbose_name='月度报表周期结束时间')),
                ('is_reported', models.BooleanField(default=True, help_text='true为生成完成', verbose_name='报表已生成状态')),
                ('notice_time', models.DateTimeField(blank=True, default=None, null=True, verbose_name='邮件通知时间')),
                ('username', models.CharField(blank=True, default='', max_length=128, verbose_name='用户名')),
                ('vo_name', models.CharField(blank=True, default='', max_length=255, verbose_name='vo名称')),
                ('owner_type', models.CharField(choices=[('user', '用户'), ('vo', 'VO组')], max_length=16, verbose_name='所属类型')),
                ('server_count', models.IntegerField(default=0, verbose_name='本月度云主机数')),
                ('server_original_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='计费金额')),
                ('server_payable_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='按量应付金额')),
                ('server_postpaid_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='按量后付费金额')),
                ('server_prepaid_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='订购预付费金额')),
                ('server_cpu_days', models.FloatField(blank=True, default=0, help_text='云服务器的CPU Day数', verbose_name='CPU*Day')),
                ('server_ram_days', models.FloatField(blank=True, default=0, help_text='云服务器的内存Gib Day数', verbose_name='内存GiB*Day')),
                ('server_disk_days', models.FloatField(blank=True, default=0, help_text='云服务器的系统盘Gib Day数', verbose_name='系统盘GiB*Day')),
                ('server_ip_days', models.FloatField(blank=True, default=0, help_text='云服务器的公网IP Day数', verbose_name='IP*Day')),
                ('bucket_count', models.IntegerField(default=0, verbose_name='本月度存储桶数')),
                ('storage_days', models.FloatField(blank=True, default=0, help_text='存储桶的存储容量GiB Day数', verbose_name='存储容量GiB*Day')),
                ('storage_original_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='计费金额')),
                ('storage_payable_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='按量应付金额')),
                ('storage_postpaid_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='按量后付费金额')),
                ('disk_count', models.IntegerField(default=0, verbose_name='本月度云硬盘数')),
                ('disk_size_days', models.FloatField(blank=True, default=0, help_text='云硬盘的容量大小GiB Day数', verbose_name='云硬盘容量GiB*Day')),
                ('disk_original_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, verbose_name='云硬盘计费金额')),
                ('disk_payable_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, verbose_name='云硬盘按量应付金额')),
                ('disk_postpaid_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, verbose_name='云硬盘按量后付费金额')),
                ('disk_prepaid_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, verbose_name='云硬盘订购预付费金额')),
            ],
            options={
                'verbose_name': '月度报表',
                'verbose_name_plural': '月度报表',
                'db_table': 'monthly_report',
                'ordering': ['-creation_time'],
            },
        ),
    ]
