#!/usr/bin/env python
"""
Written by Luckylau
Github: https://github.com/Luckylau
Email: laujunbupt0913@163.com

# Note: Example code For testing purposes only
"""

from pyVim.connect import SmartConnect, Disconnect
import atexit
from pyVmomi import vim
import sys
import argparse
import getpass
import ssl


def add_nic(vm, mac, port):
    spec = vim.vm.ConfigSpec()
    nic_changes = []
    nic_spec = vim.vm.device.VirtualDeviceSpec()
    nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add

    nic_spec.device = vim.vm.device.VirtualE1000()
    nic_spec.device.deviceInfo = vim.Description()
    nic_spec.device.deviceInfo.summary = 'vCenter API'

    nic_spec.device.backing = \
        vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
    nic_spec.device.backing.port = vim.dvs.PortConnection()
    nic_spec.device.backing.port.portgroupKey = port.portgroupKey
    nic_spec.device.backing.port.switchUuid = port.dvsUuid
    nic_spec.device.backing.port.portKey = port.key

    nic_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
    nic_spec.device.connectable.startConnected = True
    nic_spec.device.connectable.allowGuestControl = True
    nic_spec.device.connectable.connected = False
    nic_spec.device.connectable.status = 'untried'

    nic_spec.device.wakeOnLanEnabled = True
    nic_spec.device.addressType = 'assigned'
    nic_spec.device.macAddress = mac

    nic_changes.append(nic_spec)
    spec.deviceChange = nic_changes
    e = vm.ReconfigVM_Task(spec=spec)
    print("Nic card added success ...")


def get_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True
    )
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def search_port(dvs, portgroupkey):
    search_portkey = []
    criteria = vim.dvs.PortCriteria()
    criteria.connected = False
    criteria.inside = True
    criteria.portgroupKey = portgroupkey
    ports = dvs.FetchDVPorts(criteria)
    for port in ports:
        search_portkey.append(port.key)
    print(search_portkey)
    return search_portkey[0]


def get_args():
    parser = argparse.ArgumentParser(
        description='Arguments for talking to vCenter')

    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='vSphere service to connect to')

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
                        required=True,
                        action='store',
                        help='Name of the vm')

    parser.add_argument('-pg', '--portgroup',
                        required=True,
                        action='store',
                        help='Port group to connect on')

    parser.add_argument('-mac', '--macaddress',
                        required=True,
                        action='store',
                        help='Macadress of vm')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password')

    return args


def port_find(dvs, key):
    obj = None
    ports = dvs.FetchDVPorts()
    for c in ports:
        if c.key == key:
            obj = c
    return obj


def main():
    args = get_args()
    context = None
    if hasattr(ssl, "_create_unverified_context"):
        context = ssl._create_unverified_context()
    serviceInstance = SmartConnect(host=args.host,
                                   user=args.user,
                                   pwd=args.password,
                                   port=args.port,
                                   sslContext=context)
    atexit.register(Disconnect, serviceInstance)

    content = serviceInstance.RetrieveContent()
    print("Search VDS PortGroup by Name ...")
    portgroup = None
    portgroup = get_obj(content,
                        [vim.dvs.DistributedVirtualPortgroup], args.portgroup)
    if portgroup is None:
        print("Portgroup not Found in DVS ...")
        exit(0)
    print("Search Available(Unused) port for VM...")
    dvs = portgroup.config.distributedVirtualSwitch
    portKey = search_port(dvs, portgroup.key)
    port = port_find(dvs, portKey)
    print("Search VM by Name ...")
    vm = None
    vm = get_obj(content, [vim.VirtualMachine], args.vm_name)
    if vm:
        print("Find Vm , Add Nic Card ...")
        add_nic(vm, args.macaddress, port)
    else:
        print("Vm not Found ...")


if __name__ == '__main__':
    sys.exit(main())
