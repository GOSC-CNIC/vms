from .security import TEST_CASE_SECURITY


# test case settings
TEST_CASE = {
    'MONITOR_CEPH': {
        'PROVIDER': {
            'endpoint_url': 'https://aiopsmimir.cstcloud.cn/mimir/',
            'username': '',
            'password': ''
        },
        'JOB_CEPH': {
            'job_tag': 'aiops_ceph_metric'
        }
    },
    'MONITOR_SERVER': {
        'PROVIDER': {
            'endpoint_url': 'https://aiopsmimir.cstcloud.cn/mimir/',
            'username': '',
            'password': ''
        },
        'JOB_SERVER': {
            'job_tag': 'aiops_hosts_node_metric'
        }
    },
    'MONITOR_VIDEO_MEETING': {
        'PROVIDER': {
            'endpoint_url': 'http://223.193.36.46:19192',
            'username': '',
            'password': ''
        },
        'JOB_MEETING': {
            'job_tag': '45xinxihuadasha503'
        }
    },
    'MONITOR_WEBSITE': {
        'PROVIDER': {
            'endpoint_url': 'https://mimir.cstcloud.cn/mimir/',
            'username': '',
            'password': ''
        },
        'WEBSITE_URL': "http://www.acas.ac.cn/",
        'WEBSITE_SCHEME': "http://",
        'WEBSITE_HOSTNAME': "www.acas.ac.cn",
        'WEBSITE_URI': "/",
        'PROBE_LABEL': 'cstnet'    # 探针标签
    },
    'MONITOR_TIDB': {
        'PROVIDER': {
            'endpoint_url': 'https://aiopsmimir.cstcloud.cn/mimir/',
            'username': '',
            'password': ''
        },
        'JOB_TIDB': {
            'job_tag': 'aiops_tidb_metric'
        }
    },
    'LOG_SITE': {
        'PROVIDER': {
            'endpoint_url': 'https://aiopsloki.cstcloud.cn/',
            'username': '',
            'password': ''
        },
        'JOB_SITE': {
            'job_tag': 'aiops.cstcloud.cn_log'
        }
    }
}

TEST_CASE.update(TEST_CASE_SECURITY)
