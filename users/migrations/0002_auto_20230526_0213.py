# Generated by Django 3.2.13 on 2023-05-26 02:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='email',
            name='is_html',
            field=models.BooleanField(default=False, verbose_name='是否html格式信息'),
        ),
        migrations.AddField(
            model_name='email',
            name='tag',
            field=models.CharField(choices=[('year', '年度报表'), ('month', '月度报表'), ('ticket', '工单通知'), ('coupon', '代金券通知'), ('res-exp', '资源过期通知'), ('other', '其他')], default='other', max_length=16, verbose_name='标签'),
        ),
    ]
