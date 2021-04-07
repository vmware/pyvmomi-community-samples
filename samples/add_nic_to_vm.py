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
from tools import cli, pchelper, service_instance


def add_nic(si, vm, network_name):
    """
    :param si: Service Instance
    :param vm: Virtual Machine Object
    :param network_name: Name of the Virtual Network
    """
    spec = vim.vm.ConfigSpec()
    nic_changes = []

    nic_spec = vim.vm.device.VirtualDeviceSpec()
    nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add

    nic_spec.device = vim.vm.device.VirtualE1000()

    nic_spec.device.deviceInfo = vim.Description()
    nic_spec.device.deviceInfo.summary = 'vCenter API test'

    content = si.RetrieveContent()
    network = pchelper.get_obj(content, [vim.Network], network_name)
    if isinstance(network, vim.OpaqueNetwork):
        nic_spec.device.backing = \
            vim.vm.device.VirtualEthernetCard.OpaqueNetworkBackingInfo()
        nic_spec.device.backing.opaqueNetworkType = \
            network.summary.opaqueNetworkType
        nic_spec.device.backing.opaqueNetworkId = \
            network.summary.opaqueNetworkId
    else:
        nic_spec.device.backing = \
            vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
        nic_spec.device.backing.useAutoDetect = False
        nic_spec.device.backing.deviceName = network_name

    nic_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
    nic_spec.device.connectable.startConnected = True
    nic_spec.device.connectable.allowGuestControl = True
    nic_spec.device.connectable.connected = False
    nic_spec.device.connectable.status = 'untried'
    nic_spec.device.wakeOnLanEnabled = True
    nic_spec.device.addressType = 'assigned'

    nic_changes.append(nic_spec)
    spec.deviceChange = nic_changes
    e = vm.ReconfigVM_Task(spec=spec)
    print("NIC CARD ADDED")


def main():
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.PORT_GROUP)
    parser.add_optional_arguments(cli.Argument.VM_NAME, cli.Argument.UUID)
    args = parser.get_args()
    serviceInstance = service_instance.connect(args)

    vm = None
    if args.uuid:
        search_index = serviceInstance.content.searchIndex
        vm = search_index.FindByUuid(None, args.uuid, True)
    elif args.vm_name:
        content = serviceInstance.RetrieveContent()
        vm = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)

    if vm:
        add_nic(serviceInstance, vm, args.port_group)
    else:
        print("VM not found")


# start this thing
if __name__ == "__main__":
    main()
