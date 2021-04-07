#!/usr/bin/env python
# Written by Michael Rice
# Github: https://github.com/michaelrice
# Website: https://michaelrice.github.io/
# Blog: http://www.errr-online.com/
# This code has been released under the terms of the Apache 2 licenses
# http://www.apache.org/licenses/LICENSE-2.0.html


from tools import cli, service_instance, pchelper
from pyVmomi import vim

parser = cli.Parser()
parser.add_optional_arguments(cli.Argument.UUID, cli.Argument.VM_NAME)
args = parser.get_args()
si = service_instance.connect(args)

vm = None
if args.uuid:
    vm = si.content.searchIndex.FindByUuid(datacenter=None, uuid=args.uuid, vmSearch=True)
elif args.vm_name:
    content = si.RetrieveContent()
    vm = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)

if not vm:
    raise SystemExit("Unable to locate VirtualMachine.")

print("Found: {0}".format(vm.name))
print("The current powerState is: {0}".format(vm.runtime.powerState))
# This does not guarantee a reboot.
# It issues a command to the guest
# operating system asking it to perform a reboot.
# Returns immediately and does not wait for the guest
# operating system to complete the operation.
vm.RebootGuest()
print("A request to reboot the guest has been sent.")
