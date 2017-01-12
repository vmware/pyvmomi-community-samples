#!/usr/bin/env python
"""
Written by Dann Bohn
Github: https://github.com/whereismyjetpack
Email: dannbohn@gmail.com

Script to add a Hard disk to an existing VM
This is for demonstration purposes only.
I did not do a whole lot of sanity checking, etc.

Known issues:
This will not add more than 15 disks to a VM
To do that the VM needs an additional scsi controller
and I have not yet worked through that
"""
from pyVmomi import vim
from pyVmomi import vmodl
from pyVim.connect import SmartConnect, Disconnect
import atexit
import argparse
import getpass


def get_args():
    parser = argparse.ArgumentParser(
        description='Arguments for talking to vCenter')

    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='vSpehre service to connect to')

    parser.add_argument('-o', '--port',
                        type=int,
                        default=443,
                        action='store',
                        help='Port to connect on')

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='User name to use')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to use')

    parser.add_argument('-v', '--vm-name',
                        required=False,
                        action='store',
                        help='name of the vm')

    parser.add_argument('--uuid',
                        required=False,
                        action='store',
                        help='vmuuid of vm')

    parser.add_argument('--disk-type',
                        required=False,
                        action='store',
                        default='thin',
                        choices=['thick', 'thin'],
                        help='thick or thin')

    parser.add_argument('--disk-size',
                        required=True,
                        action='store',
                        help='disk size, in GB, to add to the VM')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password')

    return args


def get_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def add_disk(vm, si, disk_size, disk_type):
        spec = vim.vm.ConfigSpec()
        # get all disks on a VM, set unit_number to the next available
        unit_number = 0
        for dev in vm.config.hardware.device:
            if hasattr(dev.backing, 'fileName'):
                unit_number = int(dev.unitNumber) + 1
                # unit_number 7 reserved for scsi controller
                if unit_number == 7:
                    unit_number += 1
                if unit_number >= 16:
                    print "we don't support this many disks"
                    return
            if isinstance(dev, vim.vm.device.VirtualSCSIController):
                controller = dev
        # add disk here
        dev_changes = []
        new_disk_kb = int(disk_size) * 1024 * 1024
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.fileOperation = "create"
        disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        disk_spec.device = vim.vm.device.VirtualDisk()
        disk_spec.device.backing = \
            vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
        if disk_type == 'thin':
            disk_spec.device.backing.thinProvisioned = True
        disk_spec.device.backing.diskMode = 'persistent'
        disk_spec.device.unitNumber = unit_number
        disk_spec.device.capacityInKB = new_disk_kb
        disk_spec.device.controllerKey = controller.key
        dev_changes.append(disk_spec)
        spec.deviceChange = dev_changes
        vm.ReconfigVM_Task(spec=spec)
        print "%sGB disk added to %s" % (disk_size, vm.config.name)


def main():
    args = get_args()

    # connect this thing
    si = SmartConnect(
        host=args.host,
        user=args.user,
        pwd=args.password,
        port=args.port)
    # disconnect this thing
    atexit.register(Disconnect, si)

    vm = None
    if args.uuid:
        search_index = si.content.searchIndex
        vm = search_index.FindByUuid(None, args.uuid, True)
    elif args.vm_name:
        content = si.RetrieveContent()
        vm = get_obj(content, [vim.VirtualMachine], args.vm_name)

    if vm:
        add_disk(vm, si, args.disk_size, args.disk_type)
    else:
        print "VM not found"


# start this thing
if __name__ == "__main__":
    main()
