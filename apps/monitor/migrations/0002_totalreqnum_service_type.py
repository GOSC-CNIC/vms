# Generated by Django 4.2.9 on 2024-06-07 08:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0001_squashed_0001_initial_0011'),
    ]

    operations = [
        migrations.AddField(
            model_name='totalreqnum',
            name='service_type',
            field=models.CharField(choices=[('vms', '云主机'), ('obs', '对象存储'), ('yunkun', '本服务')], default='yunkun', max_length=16, verbose_name='服务类型'),
        ),
    ]
