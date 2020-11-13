# Generated by Django 2.2.16 on 2020-11-13 00:58

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('service', '0004_auto_20201009_0629'),
    ]

    operations = [
        migrations.AddField(
            model_name='userquota',
            name='expiration_time',
            field=models.DateTimeField(blank=True, default=None, null=True, verbose_name='过期时间'),
        ),
        migrations.AddField(
            model_name='userquota',
            name='is_email',
            field=models.BooleanField(default=False, help_text='是否邮件通知用户配额即将到期', verbose_name='是否邮件通知'),
        ),
        migrations.AddField(
            model_name='userquota',
            name='tag',
            field=models.SmallIntegerField(choices=[(1, '普通配额'), (2, '试用配额')], default=1, verbose_name='配额类型'),
        ),
        migrations.AlterField(
            model_name='userquota',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='user_quota', to=settings.AUTH_USER_MODEL, verbose_name='用户'),
        ),
    ]
