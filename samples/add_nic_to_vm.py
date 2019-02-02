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
from pyVmomi import vmodl
from tools import tasks
from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect
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

    parser.add_argument('--no-ssl',
                        action='store_true',
                        help='Skip client SSL verification')

    parser.add_argument('-v', '--vm-name',
                        required=False,
                        action='store',
                        help='name of the vm')

    parser.add_argument('--uuid',
                        required=False,
                        action='store',
                        help='vmuuid of vm')

    parser.add_argument('--port-group',
                        required=True,
                        action='store',
                        help='port group to connect on')

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
    network = get_obj(content, [vim.Network], network_name)
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
        nic_spec.device.backing.deviceName = network

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
    args = get_args()

    # connect this thing
    serviceInstance = None
    if args.no_ssl:
        serviceInstance = SmartConnectNoSSL(
            host=args.host,
            user=args.user,
            pwd=args.password,
            port=args.port)
    else:
        serviceInstance = SmartConnect(
            host=args.host,
            user=args.user,
            pwd=args.password,
            port=args.port)
    # disconnect this thing
    atexit.register(Disconnect, serviceInstance)

    vm = None
    if args.uuid:
        search_index = serviceInstance.content.searchIndex
        vm = search_index.FindByUuid(None, args.uuid, True)
    elif args.vm_name:
        content = serviceInstance.RetrieveContent()
        vm = get_obj(content, [vim.VirtualMachine], args.vm_name)

    if vm:
        add_nic(serviceInstance, vm, args.port_group)
    else:
        print("VM not found")


# start this thing
if __name__ == "__main__":
    main()
