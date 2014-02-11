# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2012 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""VNC Console Proxy Server."""

import sys

from oslo.config import cfg

from nova import config
from nova.openstack.common import log as logging
from nova import service

CONF = cfg.CONF
CONF.import_opt('consoleauth_manager', 'nova.consoleauth.manager')


def main():
    config.parse_args(sys.argv)
    logging.setup("nova")
    server = service.Service.create(binary='nova-consoleauth',
                                    topic=CONF.consoleauth_topic)
    service.serve(server)
    service.wait()
