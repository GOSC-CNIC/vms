# Generated by Django 3.2.13 on 2023-04-10 03:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0005_auto_20230320_0323'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='objectsservice',
            options={'ordering': ['sort_weight'], 'verbose_name': '对象存储服务单元接入配置', 'verbose_name_plural': '对象存储服务单元接入配置'},
        ),
        migrations.AddField(
            model_name='objectsservice',
            name='sort_weight',
            field=models.IntegerField(default=0, help_text='值越小排序越靠前', verbose_name='排序值'),
        ),
    ]
