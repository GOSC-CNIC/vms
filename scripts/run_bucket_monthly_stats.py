"""
存储桶月度趋势统计
"""

import os
import sys
from pathlib import Path

from django import setup


# 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudverse.settings')
setup()

from apps.report.workers.storage_trend import StorageSizeCounter


if __name__ == "__main__":
    StorageSizeCounter().run()
