#!/usr/bin/env python
# Copyright 2015 Michael Rice <michael@michaelrice.org>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from __future__ import print_function

from pyVmomi import vim
from tools import cli, service_instance, tasks, pchelper


parser = cli.Parser()
parser.add_optional_arguments(
    cli.Argument.UUID, cli.Argument.VM_NAME, cli.Argument.VM_IP, cli.Argument.DNS_NAME)
args = parser.get_args()
serviceInstance = service_instance.connect(args)

VM = None
if args.vm_name:
    VM = pchelper.get_obj(serviceInstance.content, [vim.VirtualMachine], args.vm_name)
elif args.uuid:
    VM = serviceInstance.content.searchIndex.FindByUuid(None, args.uuid,
                                           True,
                                           False)
elif args.dns_name:
    VM = serviceInstance.content.searchIndex.FindByDnsName(None, args.dns_name,
                                              True)
elif args.vm_ip:
    VM = serviceInstance.content.searchIndex.FindByIp(None, args.vm_ip, True)

if VM is None:
    raise SystemExit(
        "Unable to locate VirtualMachine. Arguments given: "
        "vm - {0} , uuid - {1} , name - {2} , ip - {3}"
        .format(args.vm_name, args.uuid, args.dns_name, args.vm_ip)
        )

print("Found: {0}".format(VM.name))
print("The current powerState is: {0}".format(VM.runtime.powerState))
if format(VM.runtime.powerState) == "poweredOn":
    print("Attempting to power off {0}".format(VM.name))
    TASK = VM.PowerOffVM_Task()
    tasks.wait_for_tasks(serviceInstance, [TASK])
    print("{0}".format(TASK.info.state))

print("Destroying VM from vSphere.")
TASK = VM.Destroy_Task()
tasks.wait_for_tasks(serviceInstance, [TASK])
print("Done.")
