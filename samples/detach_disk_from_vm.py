#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Written by Chris Arceneaux
# GitHub: https://github.com/carceneaux
# Email: carceneaux@thinksis.com
# Website: http://arsano.ninja
#
# Note: Example code For testing purposes only
#
# This code has been released under the terms of the Apache-2.0 license
# http://opensource.org/licenses/Apache-2.0

"""
Python program for detaching a disk from a VM without deleting the VMDK
"""

import atexit

from tools import cli, tasks, pchelper, service_instance
from pyVmomi import vmodl
from pyVmomi import vim


def get_hdd_prefix_label(language):
    language_prefix_label_mapper = {
        'English': 'Hard disk ',
        'Chinese': u'硬盘 '
    }
    return language_prefix_label_mapper.get(language)


def detach_disk_from_vm(vm, disk_number, language):
    """
    Detach first class disk from vm
    """
    hdd_prefix_label = get_hdd_prefix_label(language)
    if not hdd_prefix_label:
        raise RuntimeError('HDD prefix label could not be found')

    hdd_label = hdd_prefix_label + str(disk_number)
    virtual_hdd_device = None
    for dev in vm.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualDisk) \
                and dev.deviceInfo.label == hdd_label:
            virtual_hdd_device = dev
    if not virtual_hdd_device:
        raise RuntimeError('Virtual {} could not '
                           'be found.'.format(virtual_hdd_device))

    virtual_hdd_spec = vim.vm.device.VirtualDeviceSpec()
    virtual_hdd_spec.operation = \
        vim.vm.device.VirtualDeviceSpec.Operation.remove
    virtual_hdd_spec.device = virtual_hdd_device

    spec = vim.vm.ConfigSpec()
    spec.deviceChange = [virtual_hdd_spec]
    task = vm.ReconfigVM_Task(spec=spec)
    return task


def main():
    """
    Simple command-line program for detaching a disk from a virtual machine.
    """
    parser = cli.Parser()
    parser.add_optional_arguments(cli.Argument.VM_NAME, cli.Argument.UUID, cli.Argument.LANGUAGE)
    parser.add_custom_argument('--disk-number', required=True, help='HDD number to detach.')
    args = parser.get_args()
    si = service_instance.connect(args)

    try:
        content = si.RetrieveContent()

        # Retrieve VM
        vm = None
        if args.uuid:
            search_index = content.searchIndex
            vm = search_index.FindByUuid(None, args.uuid, True)
        elif args.vm_name:
            vm = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)

        # Detaching Disk from VM
        if vm:
            task = detach_disk_from_vm(vm, args.disk_number, args.language)
            tasks.wait_for_tasks(si, [task])
        else:
            raise RuntimeError("VM not found.")

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
