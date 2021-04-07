#!/usr/bin/env python
#
# Written by JM Lopez
# GitHub: https://github.com/jm66
# Email: jm@jmll.me
# Website: http://jose-manuel.me
#
# Note: Example code For testing purposes only
#
# This code has been released under the terms of the Apache-2.0 license
# http://opensource.org/licenses/Apache-2.0
#

import requests
from tools import cli, pchelper, service_instance
from pyVmomi import vim

_columns_four = "{0:<20} {1:<30} {2:<30} {3:<20}"

# disable  urllib3 warnings
if hasattr(requests.packages.urllib3, 'disable_warnings'):
    requests.packages.urllib3.disable_warnings()


def get_vms(content):
    obj_view = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True)
    vms_list = obj_view.view
    obj_view.Destroy()
    return vms_list


def print_vmwareware_tools_status(vm):
    print(_columns_four.format(vm.name,
                               vm.guest.toolsRunningStatus,
                               vm.guest.toolsVersion,
                               vm.guest.toolsVersionStatus2))


def main():
    parser = cli.Parser()
    parser.add_optional_arguments(cli.Argument.VM_NAME)
    args = parser.get_args()
    serviceInstance = service_instance.connect(args)

    content = serviceInstance.RetrieveContent()

    if args.vm_name:
        print('Searching for VM {}'.format(args.vm_name))
        vm_obj = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)
        if vm_obj:
            print(_columns_four.format('Name', 'Status',
                                       'Version', 'Version Status'))
            print_vmwareware_tools_status(vm_obj)
        else:
            print("VM not found")
    else:
        print(_columns_four.format('Name', 'Status', 'Version', 'Version Status'))
        for vm_obj in get_vms(content):
            print_vmwareware_tools_status(vm_obj)

# start
if __name__ == "__main__":
    main()
