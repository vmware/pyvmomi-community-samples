#!/usr/bin/env python
# VMware vSphere Python SDK
# Copyright (c) 2008-2021 VMware, Inc. All Rights Reserved.
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

from tools import cli, service_instance


parser = cli.Parser()
parser.add_required_arguments(cli.Argument.UUID)
args = parser.get_args()
serviceInstance = service_instance.connect(args)

# see:
# http://pubs.vmware.com/vsphere-55/topic/com.vmware.wssdk.apiref.doc/vim.ServiceInstanceContent.html
# http://pubs.vmware.com/vsphere-55/topic/com.vmware.wssdk.apiref.doc/vim.SearchIndex.html
search_index = serviceInstance.content.searchIndex
vm = search_index.FindByUuid(None, args.uuid, True)

if vm is None:
    print("Could not find virtual machine '{0}'".format(args.uuid))
    exit(1)

print("Found Virtual Machine")
details = {'name': vm.summary.config.name,
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
