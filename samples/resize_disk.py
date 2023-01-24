#!/usr/bin/env python
#
# Brandon Marick
# Intel Corporation
# Github: https://github.com/brmarick
#
# Based off of 'change_disk_mode.py'
#   By Max Wagner -> Github: https://github.com/wagnerm
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


def change_disk_size(si, vm_obj, disk_number, size,
                     disk_prefix_label='Hard disk '):
    """Change the disk size on a virtual hard disk.
    :param si: Service Instance
    :param vm_obj: Virtual Machine Object
    :param disk_number: Disk number.
    :param size: New Disk size in GiB.
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
    virtual_disk_spec.device.capacityInKB = size * 1024 * 1024

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
                        help='Disk number to change size.')
    # Using -n due to '-s' being used for host
    parser.add_argument('-n', '--size', required=True,
                        type=int, help='GiB disk size to change to.')
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
        change_disk_size(si, vm_obj, args.disk_number, args.size)
        print 'VM Disk {} successfully ' \
              'changed to size {}.'.format(args.disk_number,
                                           args.size)
    else:
        print "VM not found."

# start
if __name__ == "__main__":
    main()
