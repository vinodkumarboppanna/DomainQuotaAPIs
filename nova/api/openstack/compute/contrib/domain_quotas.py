# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import urlparse
import webob

from nova.api.openstack import extensions
from nova.api.openstack import wsgi
from nova.api.openstack import xmlutil
import nova.context
from nova import db
from nova import exception
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.openstack.common import strutils
from nova import quota
from nova import utils
 
QUOTAS = quota.QUOTAS
LOG = logging.getLogger(__name__)
NON_QUOTA_KEYS = ['tenant_id', 'id', 'force']


authorize_update = extensions.extension_authorizer('compute', 'quotas:update')
authorize_show = extensions.extension_authorizer('compute', 'quotas:show')
authorize_delete = extensions.extension_authorizer('compute', 'quotas:delete')


class QuotaTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('quota_set', selector='quota_set')
        root.set('id')

        for resource in QUOTAS.resources:
            elem = xmlutil.SubTemplateElement(root, resource)
            elem.text = resource

        return xmlutil.MasterTemplate(root, 1)


class DomainQuotaSetsController(wsgi.Controller):

    def __init__(self, ext_mgr):
        self.ext_mgr = ext_mgr

    def _format_quota_set(self, id, quota_set): 
        """This id can be domain_id or project_id or user_id"""
        """Convert the quota object to a result dict."""

        result = dict(id=str(id))

        for resource in QUOTAS.resources:
            result[resource] = quota_set[resource]

        return dict(quota_set=result)

    def _validate_quota_limit(self, key, limit, minimum, maximum):
        # NOTE: -1 is a flag value for unlimited
        if limit < -1:
            msg = _("Quota limit for resource " + key + " must be -1 or greater.")
            raise webob.exc.HTTPBadRequest(explanation=msg)
        if ((limit < minimum) and
           (maximum != -1 or (maximum == -1 and limit != -1))):
            msg = _("Quota limit for resource " + key + " must be greater than or equal to %s.") % minimum
            raise webob.exc.HTTPBadRequest(explanation=msg)
        if maximum != -1 and limit > maximum:
            msg = _("Quota limit for resource " + key + " must less than or equal to %s.") % maximum
            raise webob.exc.HTTPBadRequest(explanation=msg)

    def _get_quotas(self, context, id, user_id=None, project_id=None, usages=False):
        if (user_id == None) and (project_id == None):
            values = QUOTAS.get_domain_quotas(context, id, usages=usages)
        elif user_id:
            values = QUOTAS.get_domain_user_quotas(context, id, project_id, user_id,
                                            usages=usages)
        else:
            values = QUOTAS.get_domain_project_quotas(context, project_id, usages=usages)

        if usages:
            return values
        else:
            return dict((k, v['limit']) for k, v in values.items())

    @wsgi.serializers(xml=QuotaTemplate)
    def show(self, req, id):
        context = req.environ['nova.context']
        authorize_show(context)
        params = urlparse.parse_qs(req.environ.get('QUERY_STRING', ''))
        project_id = params.get('project_id', [None])[0]
        user_id = params.get('user_id', [None])[0]
        try:
            if (user_id == None) and (project_id == None):
                 nova.context.authorize_domain_context(context, id)
                 return self._format_quota_set(id, self._get_quotas(context, id))
            elif user_id:
                 nova.context.authorize_project_user_context(context, project_id, user_id)
                 return self._format_quota_set(user_id, self._get_quotas(context, id, user_id=user_id, project_id=project_id))
            else:
                 nova.context.authorize_domain_project_context(context, id, project_id)
                 return self._format_quota_set(project_id, self._get_quotas(context, id, project_id=project_id))
        except exception.NotAuthorized:
            raise webob.exc.HTTPForbidden()

    @wsgi.serializers(xml=QuotaTemplate)
    def update(self, req, id, body):
        context = req.environ['nova.context']
        authorize_update(context)
        params = urlparse.parse_qs(req.environ.get('QUERY_STRING', ''))
        project_id = params.get('project_id', [None])[0]
        user_id = params.get('user_id', [None])[0]
        
        bad_keys = []
        try:
            if (user_id == None) and (project_id == None):
                 nova.context.authorize_domain_context(context, id)
                 settable_quotas = QUOTAS.get_settable_quotas_for_domain(context, id)
            elif user_id:
                 nova.context.authorize_project_user_context(context, project_id, user_id)
                 settable_quotas = QUOTAS.get_settable_quotas_for_domain(context, id, project_id=project_id, user_id=user_id)
                 LOG.debug(_("Inside the User Quota %(key)s used: "), {'key': settable_quotas})
                 if len(settable_quotas) <= 1:
                     ## because settable_quotas dict may have project_id as one key
                     raise webob.exc.HTTPBadRequest(explanation='The quotas for the project are not set. So, first define the quotas for the project')
            else:
                 nova.context.authorize_domain_project_context(context, id, project_id)
                 settable_quotas = QUOTAS.get_settable_quotas_for_domain(context, id, project_id=project_id)
                 LOG.debug(_("Inside the Project Quota %(key)s used: "), {'key': settable_quotas})
                 if len(settable_quotas) <= 1:
                     ## because settable_quotas dict may have domain_id as one key
                     raise webob.exc.HTTPBadRequest(explanation='The quotas for the domain of this project are not set. So, first define the quotas for the domain')

        except exception.NotAuthorized:
            raise webob.exc.HTTPForbidden()

        if not self.is_valid_body(body, 'quota_set'):
            msg = _("quota_set not specified")
            raise webob.exc.HTTPBadRequest(explanation=msg)
        quota_set = body['quota_set']
        parNode_notFoundKeys = []
        if 'notfound_keys' in settable_quotas:
            parNode_notFoundKeys = settable_quotas['notfound_keys']
        for key, value in quota_set.items():
            if (key not in QUOTAS and
                    key not in NON_QUOTA_KEYS):
                bad_keys.append(key)
                continue

            if key in parNode_notFoundKeys:
                excepMessage = 'The quota value for resource ' + key + ' is not defined for the parent'
                raise webob.exc.HTTPBadRequest(explanation=excepMessage)

            if key not in NON_QUOTA_KEYS and value:
                try:
                    value = utils.validate_integer(value, key)
                except exception.InvalidInput as e:
                    LOG.warn(e.format_message())
                    raise webob.exc.HTTPBadRequest(
                        explanation=e.format_message())

        if len(bad_keys) > 0:
            msg = _("Bad key(s) %s in quota_set") % ",".join(bad_keys)
            raise webob.exc.HTTPBadRequest(explanation=msg)

        LOG.debug(_("Quota %(key)s used: "),
                              {'key': settable_quotas})

        for key, value in quota_set.items():
            if key in NON_QUOTA_KEYS or (not value and value != 0):
                continue
            value = int(value)
            if value >= 0:
                quota_value = settable_quotas.get(key)
                if quota_value and quota_value['limit'] >= 0:
                    quota_used = (quota_value['in_use'] +
                                  quota_value['reserved'])
                    LOG.debug(_("Quota %(key)s used: %(quota_used)s, "
                                "value: %(value)s."),
                              {'key': key, 'quota_used': quota_used,
                               'value': value})
                    if quota_used > value:
                        msg = (_("Quota value %(value)s for %(key)s are "
                                "less than already used and reserved "
                                "%(quota_used)s") %
                                {'value': value, 'key': key,
                                 'quota_used': quota_used})
                        raise webob.exc.HTTPBadRequest(explanation=msg)

            minimum = settable_quotas[key]['minimum']
            maximum = settable_quotas[key]['maximum']
            self._validate_quota_limit(key, value, minimum, maximum)
            try:
                if (user_id == None) and (project_id == None):
                    db.domain_quota_create(context, id, key, value)
                else:
                    db.quota_create(context, project_id, key, value,
                                user_id=user_id)
            except exception.DomainQuotaExists:
                db.domain_quota_update(context, id, key, value)
            except exception.QuotaExists:
                db.quota_update(context, project_id, key, value, user_id=user_id)
            except exception.AdminRequired:
                raise webob.exc.HTTPForbidden()
        return {'quota_set': self._get_quotas(context, id, user_id=user_id, project_id=project_id)}

    @wsgi.serializers(xml=QuotaTemplate)
    def defaults(self, req, id):
        context = req.environ['nova.context']
        authorize_show(context)
        return self._format_quota_set(id, QUOTAS.get_defaults_with_domain_driver(context))

    def delete(self, req, id):
        context = req.environ['nova.context']
        authorize_delete(context)
        params = urlparse.parse_qs(req.environ.get('QUERY_STRING', ''))

        project_id = params.get('project_id', [None])[0]
        user_id = params.get('user_id', [None])[0]

        try:
            if (user_id == None) and (project_id == None):
                 nova.context.authorize_domain_context(context, id)
                 QUOTAS.destroy_all_by_domain(context, id)
            elif user_id:
                 nova.context.authorize_project_user_context(context, project_id, user_id)
                 QUOTAS.destroy_all_by_project_and_user_in_domain(context, project_id, user_id)
            else:
                 nova.context.authorize_domain_project_context(context, id, project_id)
                 QUOTAS.destroy_all_by_project_in_domain(context, project_id)
            return webob.Response(status_int=202)
        except exception.NotAuthorized:
            raise webob.exc.HTTPForbidden()
        raise webob.exc.HTTPNotFound()


class Domain_quotas(extensions.ExtensionDescriptor):
    """Domain Quotas management support."""

    name = "DomainQuotas"
    alias = "domain-quota-sets"
    namespace = "http://docs.openstack.org/compute/ext/quotas-sets/api/v1.1"
    updated = "2014-02-04T00:00:00+00:00"

    def get_resources(self):
        resources = []

        res = extensions.ResourceExtension('domain-quota-sets',
                                            DomainQuotaSetsController(self.ext_mgr),
                                            member_actions={'defaults': 'GET'})
        resources.append(res)

        return resources
