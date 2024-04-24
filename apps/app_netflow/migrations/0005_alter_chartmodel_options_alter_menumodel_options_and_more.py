# Generated by Django 4.2.9 on 2024-04-19 06:56

from django.db import migrations, models, connection
import django.db.models.deletion
import django.utils.timezone


def clear_menu_table(apps, schema_editor):
    with connection.cursor() as cursor:
        cursor.execute('DELETE FROM `netflow_menu`;')


def do_nothing(apps, schema_editor):
    print('do nothing')


class Migration(migrations.Migration):

    dependencies = [
        ('app_netflow', '0004_rolemodel'),
    ]

    operations = [
        migrations.RunPython(clear_menu_table, reverse_code=do_nothing),
        migrations.AlterModelOptions(
            name='chartmodel',
            options={'ordering': ['sort_weight'], 'verbose_name': '图表管理', 'verbose_name_plural': '图表管理'},
        ),
        migrations.AlterModelOptions(
            name='menumodel',
            options={'ordering': ['level', 'sort_weight'], 'verbose_name': '菜单管理', 'verbose_name_plural': '菜单管理'},
        ),
        migrations.AlterModelOptions(
            name='rolemodel',
            options={'ordering': ['sort_weight'], 'verbose_name': '角色组管理', 'verbose_name_plural': '角色组管理'},
        ),
        migrations.RemoveField(
            model_name='rolemodel',
            name='menus',
        ),
        migrations.AddField(
            model_name='chartmodel',
            name='band_width',
            field=models.PositiveIntegerField(default=0, verbose_name='带宽'),
        ),
        migrations.AddField(
            model_name='chartmodel',
            name='class_name',
            field=models.CharField(blank=True, default='', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='chartmodel',
            name='class_uuid',
            field=models.CharField(blank=True, default='', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='chartmodel',
            name='creation',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='创建时间'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='chartmodel',
            name='device_ip',
            field=models.CharField(default='', max_length=255, verbose_name='IP'),
        ),
        migrations.AddField(
            model_name='chartmodel',
            name='if_address',
            field=models.CharField(blank=True, default='', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='chartmodel',
            name='if_alias',
            field=models.CharField(blank=True, default='', max_length=255, null=True, verbose_name='别名'),
        ),
        migrations.AddField(
            model_name='chartmodel',
            name='instance_name',
            field=models.CharField(blank=True, default='', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='chartmodel',
            name='instance_uuid',
            field=models.CharField(blank=True, default='', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='chartmodel',
            name='modification',
            field=models.DateTimeField(auto_now=True, verbose_name='修改时间'),
        ),
        migrations.AddField(
            model_name='chartmodel',
            name='port_name',
            field=models.CharField(default='', max_length=255, verbose_name='端口'),
        ),
        migrations.AddField(
            model_name='menumodel',
            name='charts',
            field=models.ManyToManyField(blank=True, related_name='menu_set', related_query_name='menu', to='app_netflow.chartmodel', verbose_name='流量图表集'),
        ),
        migrations.AddField(
            model_name='menumodel',
            name='father',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sub_categories', related_query_name='children', to='app_netflow.menumodel', verbose_name='上级菜单'),
        ),
        migrations.AddField(
            model_name='menumodel',
            name='level',
            field=models.PositiveSmallIntegerField(default=0, editable=False, verbose_name='菜单级别'),
        ),
        migrations.AddField(
            model_name='rolemodel',
            name='role',
            field=models.CharField(choices=[('ordinary', '普通用户'), ('admin', '管理员'), ('super-admin', '超级管理员')], default='ordinary', max_length=16, verbose_name='组类别'),
        ),
        migrations.AlterField(
            model_name='chartmodel',
            name='sort_weight',
            field=models.IntegerField(default=-1, help_text='值越小排序越靠前', verbose_name='排序值'),
        ),
        migrations.AlterField(
            model_name='menumodel',
            name='sort_weight',
            field=models.IntegerField(default=-1, help_text='值越小排序越靠前', verbose_name='排序值'),
        ),
        migrations.AlterField(
            model_name='rolemodel',
            name='name',
            field=models.CharField(max_length=255, verbose_name='组名称'),
        ),
        migrations.AlterUniqueTogether(
            name='chartmodel',
            unique_together={('device_ip', 'port_name')},
        ),
        migrations.AlterUniqueTogether(
            name='menumodel',
            unique_together={('father', 'name')},
        ),
        migrations.RemoveField(
            model_name='chartmodel',
            name='default',
        ),
        migrations.RemoveField(
            model_name='chartmodel',
            name='expression',
        ),
        migrations.RemoveField(
            model_name='chartmodel',
            name='mapping',
        ),
        migrations.RemoveField(
            model_name='chartmodel',
            name='name',
        ),
        migrations.RemoveField(
            model_name='chartmodel',
            name='status',
        ),
        migrations.RemoveField(
            model_name='chartmodel',
            name='unit',
        ),
        migrations.RemoveField(
            model_name='menumodel',
            name='category',
        ),
        migrations.RemoveField(
            model_name='menumodel',
            name='chart',
        ),
        migrations.DeleteModel(
            name='MenuCategoryModel',
        ),
    ]
