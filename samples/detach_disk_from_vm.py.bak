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

from tools import cli, tasks, disk
from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim


def get_args():
    """
    Adds additional args for detaching a disk from a vm

    -n vm_name
    -i uuid
    -d disknumber
    -l language
    """
    parser = cli.build_arg_parser()

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-n', '--vm_name',
                       action='store',
                       help='Virtual Machine name where disk is attached')

    group.add_argument('-i', '--uuid',
                       action='store',
                       help='Virtual Machine UUID where disk is attached')

    parser.add_argument('-d', '--disknumber',
                        required=True,
                        help='HDD number to detach.',
                        type=int)

    parser.add_argument('-l', '--language',
                        default='English',
                        help='Language your vcenter used.')

    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)


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

    args = get_args()

    try:
        if args.disable_ssl_verification:
            service_instance = connect.SmartConnectNoSSL(host=args.host,
                                                         user=args.user,
                                                         pwd=args.password,
                                                         port=int(args.port))
        else:
            service_instance = connect.SmartConnect(host=args.host,
                                                    user=args.user,
                                                    pwd=args.password,
                                                    port=int(args.port))

        atexit.register(connect.Disconnect, service_instance)

        content = service_instance.RetrieveContent()

        # Retrieve VM
        vm = None
        if args.uuid:
            search_index = content.searchIndex
            vm = search_index.FindByUuid(None, args.uuid, True)
        elif args.vm_name:
            vm = disk.get_obj(content, [vim.VirtualMachine], args.vm_name)

        # Detaching Disk from VM
        if vm:
            task = detach_disk_from_vm(vm, args.disknumber, args.language)
            tasks.wait_for_tasks(service_instance, [task])
        else:
            raise RuntimeError("VM not found.")

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
