#!/usr/bin/env python
"""
Written by Justin Kufro, derived Dann Bohn's add_disk_to_vm.py script
Github: https://github.com/jkufro

Script to add a raw disk to an existing VM
This is for demonstration purposes only.

Known issues (also present in add_disk_to_vm.py):
This will not add more than 15 disks to a VM
To do that the VM needs an additional scsi controller
and I have not yet worked through that
"""
from pyVmomi import vim
from pyVim.task import WaitForTasks
from tools import cli, pchelper, service_instance


def add_raw_disk(vm, si, device_name, disk_mode, disk_compatibility_mode):
    """
    Add raw disk to vm
    """
    spec = vim.vm.ConfigSpec()
    # get all disks on a VM, set unit_number to the next available
    unit_number = 0
    controller = None
    for device in vm.config.hardware.device:
        if hasattr(device.backing, 'fileName'):
            unit_number = int(device.unitNumber) + 1
            # unit_number 7 reserved for scsi controller
            if unit_number == 7:
                unit_number += 1
            if unit_number >= 16:
                print("we don't support this many disks")
                return -1
        if isinstance(device, vim.vm.device.VirtualSCSIController):
            controller = device
    if controller is None:
        print("Disk SCSI controller not found!")
        return -1
    disk_spec = vim.vm.device.VirtualDeviceSpec()
    disk_spec.fileOperation = "create"
    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    disk_spec.device = vim.vm.device.VirtualDisk()
    rdm_info = vim.vm.device.VirtualDisk.RawDiskMappingVer1BackingInfo()
    disk_spec.device.backing = rdm_info
    disk_spec.device.backing.compatibilityMode = disk_compatibility_mode
    disk_spec.device.backing.diskMode = disk_mode
    # The device_name will look something like
    #     /vmfs/devices/disks/naa.41412340757396001d7710df0fdd22a9
    disk_spec.device.backing.deviceName = device_name
    disk_spec.device.unitNumber = unit_number
    disk_spec.device.controllerKey = controller.key
    spec.deviceChange = [disk_spec]
    WaitForTasks([vm.ReconfigVM_Task(spec=spec)], si=si)
    print("Raw disk added to %s" % vm.config.name)
    return 0


def main():
    """
    Sample for adding a raw disk to vm
    """
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.DEVICE_NAME)
    parser.add_optional_arguments(
        cli.Argument.VM_NAME, cli.Argument.UUID,
        cli.Argument.DISK_MODE, cli.Argument.COMPATIBILITY_MODE)
    args = parser.get_args()
    si = service_instance.connect(args)

    vm = None
    if args.uuid:
        search_index = si.content.searchIndex
        vm = search_index.FindByUuid(None, args.uuid, True)
    elif args.vm_name:
        content = si.RetrieveContent()
        vm = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)

    if vm:
        add_raw_disk(vm, si, args.device_name,
                     args.disk_mode, args.disk_compatibility_mode)
    else:
        print("VM not found")


# start this thing
if __name__ == "__main__":
    main()
