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

import atexit
import requests
from tools import cli
from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect

_columns_four = "{0:<20} {1:<30} {2:<30} {3:<20}"

# disable  urllib3 warnings
if hasattr(requests.packages.urllib3, 'disable_warnings'):
    requests.packages.urllib3.disable_warnings()


def get_args():
    parser = cli.build_arg_parser()
    parser.add_argument('-n', '--vmname', required=False,
                        help="Name of the VirtualMachine you want to change.")
    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)


def get_obj(content, vim_type, name):
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vim_type, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def get_vms(content):

    obj_view = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True)
    vms_list = obj_view.view
    obj_view.Destroy()
    return vms_list


def print_vmwareware_tools_status(vm):
    print _columns_four.format(vm.name,
                               vm.guest.toolsRunningStatus,
                               vm.guest.toolsVersion,
                               vm.guest.toolsVersionStatus2)


def main():
    args = get_args()

    # connect to vc
    si = SmartConnect(
        host=args.host,
        user=args.user,
        pwd=args.password,
        port=args.port)
    # disconnect vc
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()

    if args.vmname:
        print 'Searching for VM {}'.format(args.vmname)
        vm_obj = get_obj(content, [vim.VirtualMachine], args.vmname)
        if vm_obj:
            print _columns_four.format('Name', 'Status',
                                       'Version', 'Version Status')
            print_vmwareware_tools_status(vm_obj)
        else:
            print "VM not found"
    else:
        print _columns_four.format('Name', 'Status',
                                   'Version', 'Version Status')
        for vm_obj in get_vms(content):
            print_vmwareware_tools_status(vm_obj)

# start
if __name__ == "__main__":
    main()
