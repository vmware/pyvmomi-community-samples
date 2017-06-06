#!/usr/bin/env python
#
# Written by JM Lopez
# Github: https://github.com/jm66
# Email: jm@jmll.me
# Website: http://jose-manuel.me
#
# Note: Example code For testing purposes only
#
# This code has been released under the terms of the Apache-2.0 license
# http://opensource.org/licenses/Apache-2.0
#

import ssl
import sys
import atexit
import requests
from tools import cli
from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
from tools import tasks

requests.packages.urllib3.disable_warnings()


def update_hardware_upgrade_scheduled(vm_obj, si, policy, vmx_id):
    # Create the Scheduled Hardware Upgrade Info
    scheduled_upgrade = vim.vm.ScheduledHardwareUpgradeInfo()
    scheduled_upgrade.upgradePolicy = policy
    scheduled_upgrade.versionKey = vmx_id
    # Add it to a new config spec
    spec = vim.vm.ConfigSpec()
    spec.scheduledHardwareUpgradeInfo = scheduled_upgrade
    task_reconfigure = vm_obj.ReconfigVM_Task(spec)
    tasks.wait_for_tasks(si, [task_reconfigure])
    return True


def get_args():
    parser = cli.build_arg_parser()
    parser.add_argument('-n', '--vmname', required=True,
                        help="Name of the VirtualMachine you want to change.")
    parser.add_argument('-l', '--policy', required=True,
                        # based on
                        # https://www.vmware.com/support/developer/converter-sdk/conv55
                        # _apireference/vim.vm.ScheduledHardwareUpgradeInfo.html
                        default='always', choices=['always', 'never', 'onSoftPowerOff'],
                        help='The policy setting used to determine when to perform '
                             'scheduled upgrades for a virtual machine.')
    parser.add_argument('-x', '--vmx', required=False,
                        default='vmx-10', type=str,
                        help='Key for target hardware version to be used '
                             'on next scheduled upgrade in the format of key.')
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
    print 'Searching for VM {}'.format(args.vmname)
    vm_obj = get_obj(content, [vim.VirtualMachine], args.vmname)

    if vm_obj:
        update_hardware_upgrade_scheduled(vm_obj, si, args.policy, args.vmx)
        vm_obj = get_obj(content, [vim.VirtualMachine], args.vmname)
        if vm_obj.config.scheduledHardwareUpgradeInfo:
            print 'Upgrade policy is now: {}'.format(vm_obj.config.scheduledHardwareUpgradeInfo.upgradePolicy)
            print 'Version key:           {}'.format(vm_obj.config.scheduledHardwareUpgradeInfo.versionKey)
    else:
        print "VM not found"

# start
if __name__ == "__main__":
    main()