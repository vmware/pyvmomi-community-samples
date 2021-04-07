#!/usr/bin/env python
# Written by Michael Rice
# Github: https://github.com/michaelrice
# Website: https://michaelrice.github.io/
# Blog: http://www.errr-online.com/
# This code has been released under the terms of the Apache 2 licenses
# http://www.apache.org/licenses/LICENSE-2.0.html


import atexit

from pyVim import connect
from tools import cli, service_instance

parser = cli.Parser()
parser.add_required_arguments(cli.Argument.UUID)
args = parser.get_args()
serviceInstance = service_instance.connect(args)

vm = serviceInstance.content.searchIndex.FindByUuid(datacenter=None, uuid=args.uuid, vmSearch=True)
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
