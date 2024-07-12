# Generated by Django 4.2.9 on 2024-07-01 07:42

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('app_alert', '0003_alertservice_ticketresolutioncategory_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='alertticket',
            name='assigned_to',
        ),
        migrations.AlterField(
            model_name='alertticket',
            name='status',
            field=models.CharField(choices=[('accepted', '已受理'), ('changed', '已转移'), ('closed', '已完成')], default='accepted', max_length=16, verbose_name='状态'),
        ),
        # migrations.CreateModel(
        #     name='TicketHandler',
        #     fields=[
        #         ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
        #         ('creation', models.DateTimeField(auto_now_add=True, help_text='提交时间', verbose_name='提交时间')),
        #         ('modification', models.DateTimeField(auto_now=True, help_text='修改时间', verbose_name='修改时间')),
        #         ('ticket', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, related_name='handler_set', related_query_name='handler', to='app_alert.alertticket', verbose_name='所属的工单')),
        #         ('user', models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_related', related_query_name='%(app_label)s_%(class)ss', to=settings.AUTH_USER_MODEL, verbose_name='处理人')),
        #     ],
        #     options={
        #         'verbose_name': '告警工单处理人',
        #         'verbose_name_plural': '告警工单处理人',
        #         'db_table': 'alert_ticket_handler',
        #         'ordering': ['-creation'],
        #     },
        # ),
        # migrations.AddField(
        #     model_name='alertticket',
        #     name='handlers',
        #     field=models.ManyToManyField(related_name='+', through='app_alert.TicketHandler', to=settings.AUTH_USER_MODEL, verbose_name='管理员'),
        # ),
        # migrations.AddConstraint(
        #     model_name='tickethandler',
        #     constraint=models.UniqueConstraint(fields=('ticket', 'user'), name='unique_together_ticket_user'),
        # ),
    ]
