# Generated by Django 2.2.16 on 2020-11-13 00:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('service', '0005_auto_20201113_0058'),
        ('servers', '0005_auto_20201019_0626'),
    ]

    operations = [
        migrations.AddField(
            model_name='server',
            name='user_quota',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='quota_servers', to='service.UserQuota', verbose_name='所属用户配额'),
        ),
        migrations.AddField(
            model_name='serverarchive',
            name='user_quota',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='server_archive_set', to='service.UserQuota', verbose_name='所属用户配额'),
        ),
    ]
