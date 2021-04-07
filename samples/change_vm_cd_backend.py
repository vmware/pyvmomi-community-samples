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

import requests
from tools import cli
from pyVmomi import vim
from tools import tasks, service_instance, pchelper

# disable  urllib3 warnings
if hasattr(requests.packages.urllib3, 'disable_warnings'):
    requests.packages.urllib3.disable_warnings()


def update_virtual_cd_backend_by_obj(si, vm_obj, cdrom_number,
                                     full_path_to_iso=None):
    """ Updates Virtual Machine CD/DVD backend device
    :param vm_obj: virtual machine object vim.VirtualMachine
    :param cdrom_number: CD/DVD drive unit number
    :param si: Service Instance
    :param full_path_to_iso: Full path to iso
    :return: True or false in case of success or error
    """

    cdrom_prefix_label = 'CD/DVD drive '
    cdrom_label = cdrom_prefix_label + str(cdrom_number)
    virtual_cdrom_device = None
    for dev in vm_obj.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualCdrom) \
                and dev.deviceInfo.label == cdrom_label:
            virtual_cdrom_device = dev

    if not virtual_cdrom_device:
        raise RuntimeError('Virtual {} could not '
                           'be found.'.format(cdrom_label))

    virtual_cd_spec = vim.vm.device.VirtualDeviceSpec()
    virtual_cd_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
    virtual_cd_spec.device = vim.vm.device.VirtualCdrom()
    virtual_cd_spec.device.controllerKey = virtual_cdrom_device.controllerKey
    virtual_cd_spec.device.key = virtual_cdrom_device.key
    virtual_cd_spec.device.connectable = \
        vim.vm.device.VirtualDevice.ConnectInfo()
    # if full_path_to_iso is provided it will mount the iso
    if full_path_to_iso:
        virtual_cd_spec.device.backing = \
            vim.vm.device.VirtualCdrom.IsoBackingInfo()
        virtual_cd_spec.device.backing.fileName = full_path_to_iso
        virtual_cd_spec.device.connectable.connected = True
        virtual_cd_spec.device.connectable.startConnected = True
    else:
        virtual_cd_spec.device.backing = \
            vim.vm.device.VirtualCdrom.RemotePassthroughBackingInfo()
    # Allowing guest control
    virtual_cd_spec.device.connectable.allowGuestControl = True

    dev_changes = [virtual_cd_spec]
    spec = vim.vm.ConfigSpec()
    spec.deviceChange = dev_changes
    task = vm_obj.ReconfigVM_Task(spec=spec)
    tasks.wait_for_tasks(si, [task])
    return True


def main():
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.VM_NAME)
    # Full path to iso. i.e. "[ds1] folder/Ubuntu.iso" If not provided, backend will set to RemotePassThrough
    parser.add_optional_arguments(cli.Argument.ISO)
    parser.add_custom_argument('--unitnumber', required=True, help='CD/DVD unit number.', type=int)
    args = parser.get_args()
    si = service_instance.connect(args)

    content = si.RetrieveContent()
    print('Searching for VM {}'.format(args.vm_name))
    vm_obj = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)

    if vm_obj:
        update_virtual_cd_backend_by_obj(si, vm_obj, args.unitnumber, args.iso)
        device_change = args.iso if args.iso else 'Client Device'
        print('VM CD/DVD {} successfully state changed to {}'.format(args.unitnumber, device_change))
    else:
        print("VM not found")


# start
if __name__ == "__main__":
    main()
