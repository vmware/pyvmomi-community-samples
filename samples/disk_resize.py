#!/usr/bin/env python
"""
Written by Sahil Gandhi
Github: https://github.com/sahilmgandhi

This code is released under the terms of the Apache 2
http://www.apache.org/licenses/LICENSE-2.0.html

Resize a disk that is attached to a VM to the desired size.
"""

import atexit
import requests
import argparse

from tools import cli
from pyVmomi import vim

from pyVim.connect import SmartConnectNoSSL, Disconnect
from tools import tasks

__author__ = 'sahilmgandhi'


def modify_disk(si, vm_obj, disk_number, size):

    disk_label = 'Hard disk ' + str(disk_number)
    vm_disk = None

    # Search for the vm disk
    for dev in vm_obj.config.hardware.device:
        if isinstance(
                dev,
                vim.vm.device.VirtualDisk) and dev.deviceInfo.label == disk_label:
            vm_disk = dev
    if not vm_disk:
        raise RuntimeError('Virtual {} could not be found.'.format(disk_label))

        # Configure the vm disk with the appropriate size
    vm_disk_spec = vim.vm.device.VirtualDeviceSpec()
    vm_disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
    vm_disk_spec.device = vm_disk
    vm_disk_spec.device.capacityInKB = size * 1024 * 1024

    # Actually go and change the vm disk
    dev_changes = []
    dev_changes.append(vm_disk_spec)
    spec = vim.vm.ConfigSpec()
    spec.deviceChange = dev_changes
    task = vm_obj.ReconfigVM_Task(spec=spec)
    tasks.wait_for_tasks(si, [task])
    return True


def get_args():

    # Parse through the arguments. Style and format taken from the other samples
    # in the samples directory
    parser = argparse.ArgumentParser()

    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='Remote host to connect to')

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='User name to use when connecting to host')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to use when connecting to host')

    parser.add_argument('-o', '--port',
                        required=False,
                        action='store',
                        help="Port to use, default is 443",
                        default=443)

    parser.add_argument('-v', '--vmname',
                        required=True,
                        help='Name of the VirtualMachine you wish to modify')

    parser.add_argument('-d', '--disk-number',
                        required=False,
                        type=int,
                        help='Disk number to change size, default is 1',
                        default=1)

    parser.add_argument('-ds', '--disksize',
                        required=True,
                        type=int,
                        help='GiB disk size to change to.')

    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)


def get_vm(content, vim_type, name):

    # Search for the VM that is being targeted
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder,
                                                        vim_type, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def main():
    args = get_args()

    # Connect to the host
    si = SmartConnectNoSSL(host=args.host,
                           user=args.user,
                           pwd=args.password,
                           port=int(args.port))
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()
    print 'Searching for VM {}'.format(args.vmname)
    vm_obj = get_vm(content, [vim.VirtualMachine], args.vmname)

    if vm_obj:
        print "Found a VM succesfully, configuring the size now."
        modify_disk(si, vm_obj, args.disk_number, args.size)
        print 'VM Hard Disk {} successfully ' 'changed to a size of {} Gb.'.format(
            args.disk_number, args.size)
    else:
        print "VM with the specified name not found."


# start
if __name__ == "__main__":
    main()
