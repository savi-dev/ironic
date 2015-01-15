# coding=utf-8
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from keystoneclient import exceptions as ksexception
from oslo.config import cfg
from six.moves.urllib import parse

from ironic.api import acl
from ironic.common import exception

CONF = cfg.CONF
acl.register_opts(CONF)

region_opts = [
    cfg.StrOpt('auth_region',
               help='Ironic keystone region name.'),
]

CONF.register_opts(region_opts, group='keystone_authtoken')

def get_service_url(service_type='baremetal', endpoint_type='internal'):
    """Wrapper for get service url from keystone service catalog."""
    auth_url = CONF.keystone_authtoken.auth_uri
    if not auth_url:
        raise exception.CatalogFailure(_('Keystone API endpoint is missing'))

    api_v3 = CONF.keystone_authtoken.auth_version == 'v3.0' or \
            'v3' in parse.urlparse(auth_url).path

    if api_v3:
        from keystoneclient.v3 import client
    else:
        from keystoneclient.v2_0 import client

    api_version = 'v3' if api_v3 else 'v2.0'
    # NOTE(lucasagomes): Get rid of the trailing '/' otherwise urljoin()
    #   fails to override the version in the URL
    auth_url = parse.urljoin(auth_url.rstrip('/'), api_version)
    try:
        ksclient = client.Client(username=CONF.keystone_authtoken.admin_user,
                        password=CONF.keystone_authtoken.admin_password,
                        tenant_name=CONF.keystone_authtoken.admin_tenant_name,
                        auth_url=auth_url)
    except ksexception.Unauthorized:
        raise exception.CatalogUnauthorized

    except ksexception.AuthorizationFailure as err:
        raise exception.CatalogFailure(_('Could not perform authorization '
                                         'process for service catalog: %s')
                                          % err)

    if not ksclient.has_service_catalog():
        raise exception.CatalogFailure(_('No keystone service catalog loaded'))

    try:
        endpoint = ksclient.service_catalog.url_for(service_type=service_type,
                                                endpoint_type=endpoint_type,
                                                region_name=CONF.keystone_authtoken.auth_region)
    except ksexception.EndpointNotFound:
        raise exception.CatalogNotFound(service_type=service_type,
                                        endpoint_type=endpoint_type)

    return endpoint
