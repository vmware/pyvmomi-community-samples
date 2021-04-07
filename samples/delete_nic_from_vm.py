#!/usr/bin/env python
"""
Written by nickcooper-zhangtonghao
Github: https://github.com/nickcooper-zhangtonghao
Email: nickcooper-zhangtonghao@opencloud.tech

Note: Example code For testing purposes only

This code has been released under the terms of the Apache-2.0 license
http://opensource.org/licenses/Apache-2.0
"""
from pyVmomi import vim
from tools import tasks, service_instance, pchelper, cli


def del_nic(si, vm, nic_number):
    """ Deletes virtual NIC based on nic number
    :param si: Service Instance
    :param vm: Virtual Machine Object
    :param nic_number: Unit Number
    :return: True if success
    """
    nic_prefix_label = 'Network adapter '
    nic_label = nic_prefix_label + str(nic_number)
    virtual_nic_device = None
    for dev in vm.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualEthernetCard)   \
                and dev.deviceInfo.label == nic_label:
            virtual_nic_device = dev

    if not virtual_nic_device:
        raise RuntimeError('Virtual {} could not be found.'.format(nic_label))

    virtual_nic_spec = vim.vm.device.VirtualDeviceSpec()
    virtual_nic_spec.operation = \
        vim.vm.device.VirtualDeviceSpec.Operation.remove
    virtual_nic_spec.device = virtual_nic_device

    spec = vim.vm.ConfigSpec()
    spec.deviceChange = [virtual_nic_spec]
    task = vm.ReconfigVM_Task(spec=spec)
    tasks.wait_for_tasks(si, [task])
    return True


def main():
    parser = cli.Parser()
    parser.add_optional_arguments(cli.Argument.UUID, cli.Argument.VM_NAME)
    parser.add_custom_argument('--unit-number', required=True, action='store', help='unit number')
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
        if del_nic(si, vm, int(args.unit_number)):
            print("Successfully deleted NIC CARD")
    else:
        print("VM not found")


# start this thing
if __name__ == "__main__":
    main()
