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
Python program for attaching a first class disk (fcd) to a virtual machine
"""

import atexit

from tools import cli, tasks, disk
from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim


def get_args():
    """
    Adds additional args for attaching a fcd to a vm

    -d datastore
    -v vdisk
    -n vm_name
    -i uuid
    """
    parser = cli.build_arg_parser()

    parser.add_argument('-d', '--datastore',
                        required=True,
                        action='store',
                        help='Datastore name where disk is located')

    parser.add_argument('-v', '--vdisk',
                        required=True,
                        action='store',
                        help='First Class Disk name to be attached')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-n', '--vm_name',
                       action='store',
                       help='Virtual Machine name where disk is attached')

    group.add_argument('-i', '--uuid',
                       action='store',
                       help='Virtual Machine UUID where disk is attached')

    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)


def attach_fcd_to_vm(vm, vdisk, datastore):
    """
    Attach already existing first class disk to vm
    """
    # Finding next available unit number
    unit_number = 0
    for dev in vm.config.hardware.device:
        if hasattr(dev.backing, 'fileName'):
            unit_number = int(dev.unitNumber) + 1
            # unit_number 7 reserved for scsi controller
            if unit_number == 7:
                unit_number += 1
            if unit_number >= 16:
                raise Exception("We don't support this many disks.")
        if isinstance(dev, vim.vm.device.VirtualSCSIController):
            controller = dev

    # Setting backings
    spec = vim.vm.ConfigSpec()
    disk_spec = vim.vm.device.VirtualDeviceSpec()
    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    disk_spec.device = vim.vm.device.VirtualDisk()
    disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
    disk_spec.device.backing.diskMode = 'persistent'
    disk_spec.device.backing.fileName = vdisk.config.backing.filePath
    disk_spec.device.backing.thinProvisioned = True
    disk_spec.device.unitNumber = unit_number
    disk_spec.device.controllerKey = controller.key

    # Creating change list
    dev_changes = []
    dev_changes.append(disk_spec)
    spec.deviceChange = dev_changes

    # Sending the request
    task = vm.ReconfigVM_Task(spec=spec)
    return task


def main():
    """
    Simple command-line program for attaching a first class disk to a vm.
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

        # Retrieve Datastore Object
        datastore = disk.get_obj(content, [vim.Datastore], args.datastore)

        # Retrieve FCD Object
        vdisk = disk.retrieve_fcd(content, datastore, args.vdisk)

        # Retrieve VM
        vm = None
        if args.uuid:
            search_index = content.searchIndex
            vm = search_index.FindByUuid(None, args.uuid, True)
        elif args.vm_name:
            vm = disk.get_obj(content, [vim.VirtualMachine], args.vm_name)

        # Attaching FCD to VM
        if vm:
            task = attach_fcd_to_vm(vm, vdisk, datastore)
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
