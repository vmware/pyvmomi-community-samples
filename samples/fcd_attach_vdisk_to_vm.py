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

from tools import cli, tasks, disk, pchelper, service_instance
from pyVmomi import vmodl
from pyVmomi import vim


def attach_fcd_to_vm(vm, vdisk):
    """
    Attach already existing first class disk to vm
    """
    # Finding next available unit number
    unit_number = 0
    controller = None
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
    if controller is None:
        print("Disk SCSI controller not found!")
        return -1

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
    dev_changes = [disk_spec]
    spec.deviceChange = dev_changes

    # Sending the request
    task = vm.ReconfigVM_Task(spec=spec)
    return task


def main():
    """
    Simple command-line program for attaching a first class disk to a vm.
    """

    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.DATASTORE_NAME, cli.Argument.FIRST_CLASS_DISK_NAME)
    parser.add_optional_arguments(cli.Argument.VM_NAME, cli.Argument.UUID)
    args = parser.get_args()
    si = service_instance.connect(args)

    try:
        content = si.RetrieveContent()

        # Retrieve Datastore Object
        datastore = pchelper.get_obj(content, [vim.Datastore], args.datastore_name)

        # Retrieve FCD Object
        vdisk = disk.retrieve_fcd(content, datastore, args.fcd_name)

        # Retrieve VM
        vm = None
        if args.uuid:
            search_index = content.searchIndex
            vm = search_index.FindByUuid(None, args.uuid, True)
        elif args.vm_name:
            vm = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)

        # Attaching FCD to VM
        if vm:
            task = attach_fcd_to_vm(vm, vdisk)
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
