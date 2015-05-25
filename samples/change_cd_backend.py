#!/usr/bin/env python
#
# Written by JM Lopez
# GitHub: https://github.com/jm66
# Email: jm@jmll.me
# Website: http://jose-manuel.me
#
# Note: Example code For testing purposes only
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

requests.packages.urllib3.disable_warnings()


def update_virtual_cd_backend(si, vm_obj, cdrom_number, full_path_to_iso=None):
    cdrom_prefix_label = 'CD/DVD drive '
    cdrom_label = cdrom_prefix_label + str(cdrom_number)
    vcd_dev = None
    for dev in vm_obj.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualCdrom) \
                and dev.deviceInfo.label == cdrom_label:
            vcd_dev = dev
    if vcd_dev:
        vcd_spec = vim.vm.device.VirtualDeviceSpec()
        vcd_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        vcd_spec.device = vim.vm.device.VirtualCdrom()
        vcd_spec.device.controllerKey = vcd_dev.controllerKey
        vcd_spec.device.key = vcd_dev.key
        vcd_spec.device.connectable = \
            vim.vm.device.VirtualDevice.ConnectInfo()
        if full_path_to_iso:
            vcd_spec.device.backing = \
                vim.vm.device.VirtualCdrom.IsoBackingInfo()
            vcd_spec.device.backing.fileName = full_path_to_iso
            vcd_spec.device.connectable.connected = True
            vcd_spec.device.connectable.startConnected = True
        else:
            vcd_spec.device.backing = \
                vim.vm.device.VirtualCdrom.RemotePassthroughBackingInfo()
        vcd_spec.device.connectable.allowGuestControl = True
    else:
        disks = list()
        for dev in vm_obj.config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualCdrom):
                disks.append(dev)
        next_unit_number = int(disks[-1].unitNumber) + 1
        current_controller_key = int(disks[-1].controllerKey)
        vcd_spec = create_virtual_cd(current_controller_key,
                                     next_unit_number,
                                     full_path_to_iso)
    dev_changes = list()
    dev_changes.append(vcd_spec)
    spec = vim.vm.ConfigSpec()
    spec.deviceChange = dev_changes
    task = vm_obj.ReconfigVM_Task(spec=spec)
    tasks.wait_for_tasks(si, [task])
    return True


def create_virtual_cd(controller_key, unit_number, full_path_to_iso=None):
    v_cd = vim.vm.device.VirtualCdrom()
    v_cd.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
    v_cd.controllerKey = controller_key
    v_cd.unitNumber = unit_number
    if full_path_to_iso:
        v_cd.backing = \
            vim.vm.device.VirtualCdrom.IsoBackingInfo()
        v_cd.backing.fileName = full_path_to_iso
        v_cd.connectable.startConnected = True
    else:
        v_cd.backing = \
            vim.vm.device.VirtualCdrom.RemotePassthroughBackingInfo()
    v_cd.connectable.allowGuestControl = True
    virtual_cd_spec = vim.vm.device.VirtualDeviceSpec()
    virtual_cd_spec.operation = "add"
    virtual_cd_spec.device = v_cd
    return virtual_cd_spec


def get_args():
    parser = cli.build_arg_parser()
    parser.add_argument('-n', '--vmname', required=True,
                        help="Name of the VirtualMachine you want to change.")
    parser.add_argument('-m', '--unitnumber', required=True,
                        help='CD/DVD unit number. If unit does not exist,'
                             ' will create a new device.', type=int)
    parser.add_argument('-i', '--iso', required=False, type=str,
                        help="Datastore ISO. i.e. [datastore1] ISO/ubuntu.iso")
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

    # connect to vc
    si = SmartConnect(
        host=args.host,
        user=args.user,
        pwd=args.password,
        port=args.port)
    # disconnect vc
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()
    print 'Searching for VM {}'.format(args.vmname)
    vm_obj = get_obj(content, [vim.VirtualMachine], args.vmname)

    if vm_obj:
        update_virtual_cd_backend(si, vm_obj, args.unitnumber, args.iso)
        backing = 'Remote Pass through' if args.iso is None else args.iso
        print 'VM CD/DVD unit {} successfully' \
              ' updated to {}'.format(args.unitnumber, backing)
    else:
        print "VM not found"

# start
if __name__ == "__main__":
    main()
