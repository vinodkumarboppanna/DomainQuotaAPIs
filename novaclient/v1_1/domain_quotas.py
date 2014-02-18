# Copyright 2011 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from novaclient import base


class DomainQuotaSet(base.Resource):

    @property
    def id(self):
        """QuotaSet does have a 'id' attribute but base.Resource needs it
        to self-refresh and QuotaSet is indexed by id"""
        return self.id

    def update(self, *args, **kwargs):
        return self.manager.update(self.id, *args, **kwargs)


class DomainQuotaSetManager(base.Manager):
    resource_class = DomainQuotaSet

    def get(self, domain_id, tenant_id=None, user_id=None):
        if hasattr(tenant_id, 'tenant_id'):
            tenant_id = tenant_id.tenant_id
        if (not user_id) and (not tenant_id):
            url = '/domain-quota-sets/%s' % (domain_id)
        elif (not user_id):
            url = '/domain-quota-sets/%s?project_id=%s' % (domain_id, tenant_id)
        else:
            url = '/domain-quota-sets/%s?project_id=%s&user_id=%s' % (domain_id, tenant_id, user_id)
        return self._get(url, "quota_set")

    def update(self, domain_id, tenant_id=None, user_id=None, metadata_items=None,
               injected_file_content_bytes=None, injected_file_path_bytes=None,
               volumes=None, gigabytes=None,
               ram=None, floating_ips=None, fixed_ips=None, instances=None,
               injected_files=None, cores=None, key_pairs=None,
               security_groups=None, security_group_rules=None):

        body = {'quota_set': {
                'metadata_items': metadata_items,
                'key_pairs': key_pairs,
                'injected_file_content_bytes': injected_file_content_bytes,
                'injected_file_path_bytes': injected_file_path_bytes,
                'volumes': volumes,
                'gigabytes': gigabytes,
                'ram': ram,
                'floating_ips': floating_ips,
                'fixed_ips': fixed_ips,
                'instances': instances,
                'injected_files': injected_files,
                'cores': cores,
                'security_groups': security_groups,
                'security_group_rules': security_group_rules}}

        for key in body['quota_set'].keys():
            if body['quota_set'][key] is None:
                body['quota_set'].pop(key)

        if (not user_id) and (not tenant_id):
            self.id = domain_id
            url = '/domain-quota-sets/%s' % (domain_id)
        elif (not user_id):
            self.id = tenant_id
            url = '/domain-quota-sets/%s?project_id=%s' % (domain_id, tenant_id)
        else:
            self.id = user_id
            url = '/domain-quota-sets/%s?project_id=%s&user_id=%s' % (domain_id, tenant_id, user_id)
        return self._update(url, body, 'quota_set')

    def defaults(self, domain_id):
        return self._get('/domain-quota-sets/%s/defaults' % domain_id,
                         'quota_set')

    def delete(self, domain_id, tenant_id=None, user_id=None):
        if (not user_id) and (not tenant_id):
           url = '/domain-quota-sets/%s' % (domain_id)
        elif (not user_id):
            url = '/domain-quota-sets/%s?project_id=%s' % (domain_id, tenant_id)
        else:
            url = '/domain-quota-sets/%s?project_id=%s&user_id=%s' % (domain_id, tenant_id, user_id)
        self._delete(url)
