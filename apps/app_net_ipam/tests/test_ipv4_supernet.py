import ipaddress

from django.urls import reverse
from django.utils import timezone as dj_timezone

from utils.test import get_or_create_user, MyAPITransactionTestCase
from apps.app_net_ipam.managers.common import NetIPamUserRoleWrapper
from apps.app_net_ipam.models import IPv4Range, IPv4Supernet
from apps.app_net_ipam.managers.ipv4_mgrs import IPv4RangeManager
from apps.app_net_ipam.permissions import IPamIPRestrictor


class IPv4SupernetTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')

        IPamIPRestrictor.add_ip_rule('127.0.0.1')
        IPamIPRestrictor.clear_cache()

    def test_create_ipv4_supernet(self):
        nt = dj_timezone.now()
        IPv4RangeManager.create_ipv4_range(
            name='已分配1', start_ip='0.0.1.0', end_ip='0.0.1.255', mask_len=24, asn=66,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.ASSIGNED.value,
            org_virt_obj=None, assigned_time=nt, admin_remark='admin1', remark='remark1'
        )

        base_url = reverse('net_ipam-api:ipam-ipv4supernet-list')
        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # start_address
        response = self.client.post(base_url, data={
            'start_address': -1, 'end_address': 255, 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # end_address
        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 2**32, 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # mask_len 0-32
        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 33,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # asn 0-4294967295
        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 24,
            'asn': 4294967295 + 1, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # AccessDenied
        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper = NetIPamUserRoleWrapper(user=self.user1)
        u1_role_wrapper.user_role = u1_role_wrapper.get_or_create_user_role()
        u1_role_wrapper.set_ipam_readonly(True)
        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        u1_role_wrapper = NetIPamUserRoleWrapper(user=self.user1)
        u1_role_wrapper.set_ipam_readonly(False)
        u1_role_wrapper.set_ipam_admin(True)

        # start_address > end_address
        response = self.client.post(base_url, data={
            'start_address': 256, 'end_address': 255, 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # start_address, end_address, mask_len, not in same network
        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 256, 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 25,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        response = self.client.post(base_url, data={
            'start_address': 0, 'end_address': 255, 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'creation_time', 'status', 'update_time',
                           'remark', 'start_address', 'end_address', 'mask_len', 'asn'], response.data)
        supernet1 = IPv4Supernet.objects.get(id=response.data['id'])
        self.assertEqual(supernet1.start_address, int(ipaddress.IPv4Address('0.0.0.0')))
        self.assertEqual(supernet1.end_address, int(ipaddress.IPv4Address('0.0.0.255')))
        self.assertEqual(supernet1.mask_len, 24)
        self.assertEqual(supernet1.status, IPv4Supernet.Status.OUT_WAREHOUSE.value)
        self.assertEqual(supernet1.asn, 88)
        self.assertEqual(supernet1.name, '0.0.0.0/24')
        self.assertEqual(supernet1.operator, self.user1.username)
        self.assertEqual(supernet1.used_ip_count, 0)
        self.assertEqual(supernet1.total_ip_count, 256)

        # 存在重叠
        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 200, 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={
            'start_address': 100, 'end_address': 256, 'mask_len': 23,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={
            'start_address': 255, 'end_address': 512, 'mask_len': 23,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        response = self.client.post(base_url, data={
            'start_address': 256, 'end_address': 511, 'mask_len': 24,
            'asn': 4294967295, 'admin_remark': ''
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'status', 'start_address', 'end_address', 'mask_len', 'asn', 'remark',
                           'creation_time', 'update_time', 'operator', 'used_ip_count', 'total_ip_count'
                           ], response.data)
        supernet1 = IPv4Supernet.objects.get(id=response.data['id'])
        self.assertEqual(supernet1.start_address, int(ipaddress.IPv4Address('0.0.1.0')))
        self.assertEqual(supernet1.end_address, int(ipaddress.IPv4Address('0.0.1.255')))
        self.assertEqual(supernet1.mask_len, 24)
        self.assertEqual(supernet1.status, IPv4Supernet.Status.IN_WAREHOUSE.value)
        self.assertEqual(supernet1.asn, 4294967295)
        self.assertEqual(supernet1.name, '0.0.1.0/24')
        self.assertEqual(supernet1.operator, self.user1.username)
        self.assertEqual(supernet1.used_ip_count, 256)
        self.assertEqual(supernet1.total_ip_count, 256)
