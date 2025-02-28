from apps.app_alert.models import AlertModel
from apps.app_alert.models import ResolvedAlertModel
from django.db.models import Q
from django.forms.models import model_to_dict
from apps.app_monitor.models import MonitorJobServer
from apps.app_monitor.models import MonitorWebsite
from apps.app_monitor.models import MonitorJobCeph
from apps.app_monitor.models import MonitorJobTiDB
from apps.app_alert.utils.utils import DateUtils
from django.db.utils import IntegrityError


def move_to_resolved(obj):
    item = model_to_dict(obj)
    item["id"] = obj.id
    item["ticket"] = obj.ticket
    item["modification"] = DateUtils.timestamp()
    status = item.get('status')
    if status == AlertModel.AlertStatus.FIRING.value:
        item['status'] = AlertModel.AlertStatus.RESOLVED.value
    try:
        ResolvedAlertModel.objects.create(**item)
    except IntegrityError as e:
        pass
    obj.delete()


class UserMonitorUnit:
    def __init__(self, request):
        self.clusters = UserMonitor(request).monitor_cluster_list()
        self.url_hash_list = UserMonitor(request).website_list()


class UserMonitor(object):
    def __init__(self, request):
        self.request = request

    def monitor_cluster_list(self):
        metric_tag_list = self.server_list() + self.tidb_list() + self.ceph_list()
        log_tag_list = [_.replace("_metric", "_log") for _ in metric_tag_list if _.endswith("_metric")]
        return list(set(metric_tag_list + log_tag_list))

    def server_list(self):
        user = self.request.user
        queryset = MonitorJobServer.objects.select_related('org_data_center__organization').all()
        if user.is_authenticated and user.is_federal_admin():
            pass
        else:
            queryset = queryset.filter(Q(users__id=user.id) | Q(org_data_center__users__id=user.id))
        queryset = queryset.distinct()
        job_tag_list = [_.job_tag for _ in queryset]
        return job_tag_list

    def tidb_list(self):
        user = self.request.user
        queryset = MonitorJobTiDB.objects.select_related('org_data_center__organization').all()
        if user.is_authenticated and user.is_federal_admin():
            pass
        else:
            queryset = queryset.filter(Q(users__id=user.id) | Q(org_data_center__users__id=user.id))
        queryset = queryset.distinct()
        job_tag_list = [_.job_tag for _ in queryset]
        return job_tag_list

    def ceph_list(self):
        user = self.request.user
        queryset = MonitorJobCeph.objects.select_related('org_data_center__organization').all()
        if user.is_authenticated and user.is_federal_admin():
            pass
        else:
            queryset = queryset.filter(Q(users__id=user.id) | Q(org_data_center__users__id=user.id))
        queryset = queryset.distinct()
        job_tag_list = [_.job_tag for _ in queryset]
        return job_tag_list

    def website_list(self):
        user = self.request.user
        user_id = user.id
        queryset = MonitorWebsite.objects.select_related('user', 'odc').all()
        q = Q(user_id=user_id) | Q(odc__users__id=user_id)
        queryset = queryset.filter(q).distinct()
        url_hash_list = [_.url_hash for _ in queryset]
        return url_hash_list


class AlertQuerysetFilter(object):
    """
    通过当前用户
    获取管理集群列表
    对告警信息进行过滤
    """

    def __init__(self, request):
        self.request = request
        self.qs_list = [AlertModel.objects.all(), ResolvedAlertModel.objects.all()]

    def filter(self):
        if self.request.user.is_superuser:
            return self.qs_list
        user_units = UserMonitorUnit(self.request)
        qs_list = []
        for model in self.qs_list:
            qs = model.filter(Q(cluster__in=user_units.clusters) | Q(fingerprint__in=user_units.url_hash_list))
            qs_list.append(qs)
        return qs_list


class AlertChoiceHandler(object):
    def __init__(self, request):
        self.filtered_qs_list = AlertQuerysetFilter(request=request).filter()
        self.field_list = ["name", "cluster", ]

    def get(self):
        result = dict()
        for field in self.field_list:
            result.update(self.counting_by_field(field))
        return result

    def counting_by_field(self, field):
        values = []
        for qs in self.filtered_qs_list:
            alert = qs.values(field).distinct().order_by(field)
            value = [_.get(field) for _ in alert]
            values.extend(value)
        return {field: sorted(list(set(values)))}


class EmailNotificationCleaner(object):

    def start(self, data):
        data = [dict(_) for _ in data]
        items = []
        alert_id_list = [_.get("alert") for _ in data]
        firing = AlertModel.objects.filter(id__in=alert_id_list)
        resolved = ResolvedAlertModel.objects.filter(id__in=alert_id_list)
        mapping = dict()
        for _ in firing:
            mapping[_.id] = _
        for _ in resolved:
            mapping[_.id] = _
        for obj in data:
            alert_id = obj.get("alert")
            alert = model_to_dict(mapping.get(alert_id))
            alert["monitor_cluster"] = alert.get('cluster')
            obj.update({"alert": alert})
            items.append(obj)
        return items
