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
from pyVmomi import vmodl
from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect
from pyVim.task import WaitForTasks
from tools import cli
import atexit
import argparse
import getpass


def get_args():
    parser = cli.build_arg_parser()

    parser.add_argument('-v', '--vm-name',
                        required=False,
                        action='store',
                        help='name of the vm')

    parser.add_argument('--uuid',
                        required=False,
                        action='store',
                        help='vmuuid of vm')

    parser.add_argument('--device-name',
                        required=True,
                        action='store',
                        help=('The device name. Might look like '
                              '"/vmfs/devices/disks/naa.*". '
                              'See vim.vm.device.VirtualDisk.'
                              'RawDiskMappingVer1BackingInfo documentation.'))

    parser.add_argument('--disk-mode',
                        required=False,
                        action='store',
                        default='independent_persistent',
                        choices=['append',
                                 'independent_nonpersistent',
                                 'independent_persistent',
                                 'nonpersistent',
                                 'persistent',
                                 'undoable'],
                        help=('See vim.vm.device.VirtualDiskOption.DiskMode '
                              'documentation.'))

    parser.add_argument('--compatibility-mode',
                        required=False,
                        default='virtualMode',
                        choices=['physicalMode', 'virtualMode'],
                        action='store',
                        help=('See vim.vm.device.VirtualDiskOption.'
                              'CompatibilityMode documentation.'))

    return cli.prompt_for_password(parser.parse_args())


def get_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def add_raw_disk(vm, si, device_name, disk_mode, compatibility_mode):
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
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.fileOperation = "create"
        disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        disk_spec.device = vim.vm.device.VirtualDisk()
        rdm_info = vim.vm.device.VirtualDisk.RawDiskMappingVer1BackingInfo()
        disk_spec.device.backing = rdm_info
        disk_spec.device.backing.compatibilityMode = compatibility_mode
        disk_spec.device.backing.diskMode = disk_mode
        # The device_name will look something like
        #     /vmfs/devices/disks/naa.41412340757396001d7710df0fdd22a9
        disk_spec.device.backing.deviceName = device_name
        disk_spec.device.unitNumber = unit_number
        disk_spec.device.controllerKey = controller.key
        spec.deviceChange = [disk_spec]
        WaitForTasks([vm.ReconfigVM_Task(spec=spec)], si=si)
        print "Raw disk added to %s" % (vm.config.name)


def main():
    args = get_args()

    # create the service instance
    si = None
    if args.disable_ssl_verification:
        si = SmartConnectNoSSL(host=args.host,
                               user=args.user,
                               pwd=args.password,
                               port=args.port)
    else:
        si = SmartConnect(host=args.host,
                          user=args.user,
                          pwd=args.password,
                          port=args.port)

    # disconnect the service instance at program exit
    atexit.register(Disconnect, si)

    vm = None
    if args.uuid:
        search_index = si.content.searchIndex
        vm = search_index.FindByUuid(None, args.uuid, True)
    elif args.vm_name:
        content = si.RetrieveContent()
        vm = get_obj(content, [vim.VirtualMachine], args.vm_name)

    if vm:
        add_raw_disk(vm, si, args.device_name,
                     args.disk_mode, args.compatibility_mode)
    else:
        print "VM not found"


# start this thing
if __name__ == "__main__":
    main()
