#!/usr/bin/env python
#
# Max Wagner
# Github: https://github.com/wagnerm
#
# This code has been released under the terms of the Apache-2.0 license
# http://opensource.org/licenses/Apache-2.0
#

import atexit
import requests
from tools import cli
from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
from tools import tasks


# disable urllib3 warnings
if hasattr(requests.packages.urllib3, 'disable_warnings'):
    requests.packages.urllib3.disable_warnings()


def change_disk_mode(si, vm_obj, disk_number, mode,
                     disk_prefix_label='Hard disk '):
    """Change the disk mode on a virtual hard disk.
    :param si: Service Instance
    :param vm_obj: Virtual Machine Object
    :param disk_number: Disk number.
    :param mode: New disk mode.
    :param disk_prefix_label: Prefix name of disk.
    :return: True if success
    """
    disk_label = disk_prefix_label + str(disk_number)
    virtual_disk_device = None

    # Find the disk device
    for dev in vm_obj.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualDisk) \
                and dev.deviceInfo.label == disk_label:
            virtual_disk_device = dev
    if not virtual_disk_device:
        raise RuntimeError('Virtual {} could not be found.'.format(disk_label))

    virtual_disk_spec = vim.vm.device.VirtualDeviceSpec()
    virtual_disk_spec.operation = \
        vim.vm.device.VirtualDeviceSpec.Operation.edit
    virtual_disk_spec.device = virtual_disk_device
    virtual_disk_spec.device.backing.diskMode = mode

    dev_changes = []
    dev_changes.append(virtual_disk_spec)
    spec = vim.vm.ConfigSpec()
    spec.deviceChange = dev_changes
    task = vm_obj.ReconfigVM_Task(spec=spec)
    tasks.wait_for_tasks(si, [task])
    return True


def get_args():
    parser = cli.build_arg_parser()
    parser.add_argument('-v', '--vmname', required=True,
                        help='Name of the VirtualMachine you want to change.')
    parser.add_argument('-d', '--disk-number', required=True,
                        help='Disk number to change mode.')
    parser.add_argument('-m', '--mode', required=True,
                        choices=['independent_persistent',
                                 'persistent',
                                 'independent_nonpersistent',
                                 'nonpersistent',
                                 'undoable',
                                 'append'])
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

    si = SmartConnect(host=args.host,
                      user=args.user,
                      pwd=args.password,
                      port=int(args.port))
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()
    print 'Searching for VM {}'.format(args.vmname)
    vm_obj = get_obj(content, [vim.VirtualMachine], args.vmname)

    if vm_obj:
        change_disk_mode(si, vm_obj, args.disk_number, args.mode)
        print 'VM Disk {} successfully ' \
              'changed to mode {}.'.format(args.disk_number,
                                           args.mode)
    else:
        print "VM not found."

# start
if __name__ == "__main__":
    main()
