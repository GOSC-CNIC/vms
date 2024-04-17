import os
import sys
from pathlib import Path

from django import setup


# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudverse.settings')
setup()

from apps.report.workers.report_generator import MonthlyReportGenerator, MonthlyReportNotifier


if __name__ == "__main__":
    """
    生成月度报表，并发送给用户

    遍历查询欠费的云主机和存储桶，记录到report中各资源的欠费记录表中
    """
    try:
        from apps.report.workers.server_notifier import ArrearServerReporter
        from apps.report.workers.storage_trend import ArrearBucketReporter
        ArrearServerReporter().run()
        ArrearBucketReporter().run()
    except Exception as exc:
        pass

    mrg = MonthlyReportGenerator(log_stdout=True)
    ok = mrg.run()
    if ok:
        MonthlyReportNotifier(report_data=mrg.report_period_date, log_stdout=True).run()
