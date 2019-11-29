#!/usr/bin/env python
# VMware vSphere Python SDK
# Copyright (c) 2008-2013 VMware, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import atexit
import ssl

from pyVim import connect

from tools import cli


def get_args():
    parser = cli.build_arg_parser()

    parser.add_argument('--uuid',
                        required=True,
                        action='store',
                        help='Instance UUID of the VM to look for.')

    args = parser.parse_args()
    return cli.prompt_for_password(args)

args = get_args()

sslContext = None
if args.disable_ssl_verification:
    sslContext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    sslContext.verify_mode = ssl.CERT_NONE

# form a connection...
si = connect.SmartConnect(host=args.host, user=args.user, pwd=args.password,
                          port=args.port, sslContext=sslContext)

# doing this means you don't need to remember to disconnect your script/objects
atexit.register(connect.Disconnect, si)

# see:
# http://pubs.vmware.com/vsphere-55/topic/com.vmware.wssdk.apiref.doc/vim.ServiceInstanceContent.html
# http://pubs.vmware.com/vsphere-55/topic/com.vmware.wssdk.apiref.doc/vim.SearchIndex.html
search_index = si.content.searchIndex
vm = search_index.FindByUuid(None, args.uuid, True, True)

if vm is None:
    print("Could not find virtual machine '{0}'".format(args.uuid))
    exit(1)

print("Found Virtual Machine")
details = {'name': vm.summary.config.name,
           'domain name': vm.guest.hostName,
           'ip address': vm.guest.ipAddress,
           'instance UUID': vm.summary.config.instanceUuid,
           'bios UUID': vm.summary.config.uuid,
           'path to VM': vm.summary.config.vmPathName,
           'guest OS id': vm.summary.config.guestId,
           'guest OS name': vm.summary.config.guestFullName,
           'host name': vm.runtime.host.name,
           'last booted timestamp': vm.runtime.bootTime,
           }

for name, value in details.items():
    print("{0:{width}{base}}: {1}".format(name, value, width=25, base='s'))
