#!/usr/bin/env python
#
# Written by Michael Rice
# Github: https://github.com/michaelrice
# Website: https://michaelrice.github.io/
# Blog: http://www.errr-online.com/
#
# This code is released under the terms of the Apache 2
# http://www.apache.org/licenses/LICENSE-2.0.html
#
# Example script to reboot a VirtualMachine

from tools import cli, service_instance, tasks, pchelper
from pyVmomi import vim


parser = cli.Parser()
parser.add_optional_arguments(cli.Argument.VM_NAME, cli.Argument.DNS_NAME, cli.Argument.UUID, cli.Argument.VM_IP)
args = parser.get_args()
serviceInstance = service_instance.connect(args)

VM = None
if args.uuid:
    VM = serviceInstance.content.searchIndex.FindByUuid(None, args.uuid, True, True)
elif args.dns_name:
    VM = serviceInstance.content.searchIndex.FindByDnsName(None, args.dns_name, True)
elif args.vm_ip:
    VM = serviceInstance.content.searchIndex.FindByIp(None, args.vm_ip, True)
elif args.vm_name:
    content = serviceInstance.RetrieveContent()
    VM = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)

if VM is None:
    raise SystemExit("Unable to locate VirtualMachine.")

print("Found: {0}".format(VM.name))
print("The current powerState is: {0}".format(VM.runtime.powerState))
TASK = VM.ResetVM_Task()
tasks.wait_for_tasks(serviceInstance, [TASK])
print("its done.")
