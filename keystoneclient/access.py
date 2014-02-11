# Copyright 2012 Nebula, Inc.
#
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import datetime

from keystoneclient.openstack.common import timeutils
from keystoneclient import service_catalog
import logging
_logger = logging.getLogger(__name__)

# gap, in seconds, to determine whether the given token is about to expire
STALE_TOKEN_DURATION = 30


class AccessInfo(dict):
    """Encapsulates a raw authentication token from keystone.

    Provides helper methods for extracting useful values from that token.

    """

    @classmethod
    def factory(cls, resp=None, body=None, **kwargs):
        """Create AccessInfo object given a successful auth response & body
           or a user-provided dict.
        """
        _logger.debug("entering factory")
        if body is not None or len(kwargs):
            if AccessInfoV3.is_valid(body, **kwargs):
                _logger.debug("222222")
                token = None
                if resp:
                    token = resp.headers['X-Subject-Token']
                if body:
                    return AccessInfoV3(token, **body['token'])
                else:
                    return AccessInfoV3(token, **kwargs)
            elif AccessInfoV2.is_valid(body, **kwargs):
                _logger.debug("333332")
                if body:
                    return AccessInfoV2(**body['access'])
                else:
                    return AccessInfoV2(**kwargs)
            else:
                raise NotImplementedError('Unrecognized auth response')
        else:
            _logger.debug("111111")
            return AccessInfoV2(**kwargs)

    def __init__(self, *args, **kwargs):
        super(AccessInfo, self).__init__(*args, **kwargs)
        self.service_catalog = service_catalog.ServiceCatalog.factory(
            resource_dict=self, region_name=self.get('region_name'))

    def will_expire_soon(self, stale_duration=None):
        """Determines if expiration is about to occur.

        :return: boolean : true if expiration is within the given duration

        """
        stale_duration = (STALE_TOKEN_DURATION if stale_duration is None
                          else stale_duration)
        norm_expires = timeutils.normalize_time(self.expires)
        # (gyee) should we move auth_token.will_expire_soon() to timeutils
        # instead of duplicating code here?
        soon = (timeutils.utcnow() + datetime.timedelta(
                seconds=stale_duration))
        return norm_expires < soon

    @classmethod
    def is_valid(cls, body, **kwargs):
        """Determines if processing v2 or v3 token given a successful
        auth body or a user-provided dict.

        :return: boolean : true if auth body matches implementing class
        """
        raise NotImplementedError()

    def has_service_catalog(self):
        """Returns true if the authorization token has a service catalog.

        :returns: boolean
        """
        raise NotImplementedError()

    @property
    def auth_token(self):
        """Returns the token_id associated with the auth request, to be used
        in headers for authenticating OpenStack API requests.

        :returns: str
        """
        raise NotImplementedError()

    @property
    def expires(self):
        """Returns the token expiration (as datetime object)

        :returns: datetime
        """
        raise NotImplementedError()

    @property
    def username(self):
        """Returns the username associated with the authentication request.
        Follows the pattern defined in the V2 API of first looking for 'name',
        returning that if available, and falling back to 'username' if name
        is unavailable.

        :returns: str
        """
        raise NotImplementedError()

    @property
    def user_id(self):
        """Returns the user id associated with the authentication request.

        :returns: str
        """
        raise NotImplementedError()

    @property
    def user_domain_id(self):
        """Returns the domain id of the user associated with the authentication
        request.

        For v2, it always returns 'default' which may be different from the
        Keystone configuration.

        :returns: str
        """
        raise NotImplementedError()

    @property
    def user_domain_name(self):
        """Returns the domain name of the user associated with the
        authentication request.

        For v2, it always returns 'Default' which may be different from the
        Keystone configuration.

        :returns: str
        """
        raise NotImplementedError()

    @property
    def domain_name(self):
        """Returns the domain name associated with the authentication token.

        :returns: str or None (if no domain associated with the token)
        """
        raise NotImplementedError()

    @property
    def domain_id(self):
        """Returns the domain id associated with the authentication token.

        :returns: str or None (if no domain associated with the token)
        """
        raise NotImplementedError()

    @property
    def project_name(self):
        """Returns the project name associated with the authentication request.

        :returns: str or None (if no project associated with the token)
        """
        raise NotImplementedError()

    @property
    def tenant_name(self):
        """Synonym for project_name."""
        return self.project_name

    @property
    def scoped(self):
        """Returns true if the authorization token was scoped to a tenant
           (project), and contains a populated service catalog.

           This is deprecated, use project_scoped instead.

        :returns: bool
        """
        raise NotImplementedError()

    @property
    def project_scoped(self):
        """Returns true if the authorization token was scoped to a tenant
           (project).

        :returns: bool
        """
        raise NotImplementedError()

    @property
    def domain_scoped(self):
        """Returns true if the authorization token was scoped to a domain.

        :returns: bool
        """
        raise NotImplementedError()

    @property
    def trust_id(self):
        """Returns the trust id associated with the authentication token.

        :returns: str or None (if no trust associated with the token)
        """
        raise NotImplementedError()

    @property
    def trust_scoped(self):
        """Returns true if the authorization token was scoped as delegated in a
        trust, via the OS-TRUST v3 extension.

        :returns: bool
        """
        raise NotImplementedError()

    @property
    def project_id(self):
        """Returns the project ID associated with the authentication
        request, or None if the authentication request wasn't scoped to a
        project.

        :returns: str or None (if no project associated with the token)
        """
        raise NotImplementedError()

    @property
    def tenant_id(self):
        """Synonym for project_id."""
        return self.project_id

    @property
    def project_domain_id(self):
        """Returns the domain id of the project associated with the
        authentication request.

        For v2, it returns 'default' if a project is scoped or None which may
        be different from the keystone configuration.

        :returns: str
        """
        raise NotImplementedError()

    @property
    def project_domain_name(self):
        """Returns the domain name of the project associated with the
        authentication request.

        For v2, it returns 'Default' if a project is scoped or None  which may
        be different from the keystone configuration.

        :returns: str
        """
        raise NotImplementedError()

    @property
    def auth_url(self):
        """Returns a tuple of URLs from publicURL and adminURL for the service
        'identity' from the service catalog associated with the authorization
        request. If the authentication request wasn't scoped to a tenant
        (project), this property will return None.

        :returns: tuple of urls
        """
        raise NotImplementedError()

    @property
    def management_url(self):
        """Returns the first adminURL for 'identity' from the service catalog
        associated with the authorization request, or None if the
        authentication request wasn't scoped to a tenant (project).

        :returns: tuple of urls
        """
        raise NotImplementedError()

    @property
    def version(self):
        """Returns the version of the auth token from identity service.

        :returns: str
        """
        return self.get('version')


class AccessInfoV2(AccessInfo):
    """An object for encapsulating a raw v2 auth token from identity
       service.
    """

    def __init__(self, *args, **kwargs):
        super(AccessInfo, self).__init__(*args, **kwargs)
        self.update(version='v2.0')
        self.service_catalog = service_catalog.ServiceCatalog.factory(
            resource_dict=self,
            token=self['token']['id'],
            region_name=self.get('region_name'))

    @classmethod
    def is_valid(cls, body, **kwargs):
        if body:
            return 'access' in body
        elif kwargs:
            return kwargs.get('version') == 'v2.0'
        else:
            return False

    def has_service_catalog(self):
        return 'serviceCatalog' in self

    @property
    def auth_token(self):
        return self['token']['id']

    @property
    def expires(self):
        return timeutils.parse_isotime(self['token']['expires'])

    @property
    def username(self):
        return self['user'].get('name', self['user'].get('username'))

    @property
    def user_id(self):
        return self['user']['id']

    @property
    def user_domain_id(self):
        return 'default'

    @property
    def user_domain_name(self):
        return 'Default'

    @property
    def domain_name(self):
        return None

    @property
    def domain_id(self):
        return None

    @property
    def project_name(self):
        try:
            tenant_dict = self['token']['tenant']
        except KeyError:
            pass
        else:
            return tenant_dict.get('name')

        # pre grizzly
        try:
            return self['user']['tenantName']
        except KeyError:
            pass

        # pre diablo, keystone only provided a tenantId
        try:
            return self['token']['tenantId']
        except KeyError:
            pass

    @property
    def scoped(self):
        if ('serviceCatalog' in self
                and self['serviceCatalog']
                and 'tenant' in self['token']):
            return True
        return False

    @property
    def project_scoped(self):
        return 'tenant' in self['token']

    @property
    def domain_scoped(self):
        return False

    @property
    def trust_id(self):
        return self.get('trust', {}).get('id')

    @property
    def trust_scoped(self):
        return 'trust' in self

    @property
    def project_id(self):
        try:
            tenant_dict = self['token']['tenant']
        except KeyError:
            pass
        else:
            return tenant_dict.get('id')

        # pre grizzly
        try:
            return self['user']['tenantId']
        except KeyError:
            pass

        # pre diablo
        try:
            return self['token']['tenantId']
        except KeyError:
            pass

    @property
    def project_domain_id(self):
        if self.project_id:
            return 'default'

    @property
    def project_domain_name(self):
        if self.project_id:
            return 'Default'

    @property
    def auth_url(self):
        if self.service_catalog:
            return self.service_catalog.get_urls(service_type='identity',
                                                 endpoint_type='publicURL')
        else:
            return None

    @property
    def management_url(self):
        if self.service_catalog:
            return self.service_catalog.get_urls(service_type='identity',
                                                 endpoint_type='adminURL')
        else:
            return None


class AccessInfoV3(AccessInfo):
    """An object for encapsulating a raw v3 auth token from identity
       service.
    """

    def __init__(self, token, *args, **kwargs):
        super(AccessInfo, self).__init__(*args, **kwargs)
        self.update(version='v3')
        self.service_catalog = service_catalog.ServiceCatalog.factory(
            resource_dict=self,
            token=token,
            region_name=self.get('region_name'))
        if token:
            self.update(auth_token=token)

    @classmethod
    def is_valid(cls, body, **kwargs):
        if body:
            return 'token' in body
        elif kwargs:
            return kwargs.get('version') == 'v3'
        else:
            return False

    def has_service_catalog(self):
        return 'catalog' in self

    @property
    def auth_token(self):
        return self['auth_token']

    @property
    def expires(self):
        return timeutils.parse_isotime(self['expires_at'])

    @property
    def user_id(self):
        return self['user']['id']

    @property
    def user_domain_id(self):
        return self['user']['domain']['id']

    @property
    def user_domain_name(self):
        return self['user']['domain']['name']

    @property
    def username(self):
        return self['user']['name']

    @property
    def domain_name(self):
        domain = self.get('domain')
        if domain:
            return domain['name']

    @property
    def domain_id(self):
        domain = self.get('domain')
        if domain:
            return domain['id']

    @property
    def project_id(self):
        project = self.get('project')
        if project:
            return project['id']

    @property
    def project_domain_id(self):
        project = self.get('project')
        if project:
            return project['domain']['id']

    @property
    def project_domain_name(self):
        project = self.get('project')
        if project:
            return project['domain']['name']

    @property
    def project_name(self):
        project = self.get('project')
        if project:
            return project['name']

    @property
    def scoped(self):
        return ('catalog' in self and self['catalog'] and 'project' in self)

    @property
    def project_scoped(self):
        return 'project' in self

    @property
    def domain_scoped(self):
        return 'domain' in self

    @property
    def trust_id(self):
        return self.get('OS-TRUST:trust', {}).get('id')

    @property
    def trust_scoped(self):
        return 'OS-TRUST:trust' in self

    @property
    def auth_url(self):
        if self.service_catalog:
            return self.service_catalog.get_urls(service_type='identity',
                                                 endpoint_type='public')
        else:
            return None

    @property
    def management_url(self):
        if self.service_catalog:
            return self.service_catalog.get_urls(service_type='identity',
                                                 endpoint_type='admin')
        else:
            return None
