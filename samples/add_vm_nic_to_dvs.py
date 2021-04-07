#!/usr/bin/env python
"""
Written by Luckylau
Github: https://github.com/Luckylau
Email: laujunbupt0913@163.com

# Note: Example code For testing purposes only
"""

from pyVmomi import vim
from tools import cli, service_instance, pchelper
import sys
import argparse
import getpass


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
    vm.ReconfigVM_Task(spec=spec)
    print("Nic card added success ...")


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


def port_find(dvs, key):
    obj = None
    ports = dvs.FetchDVPorts()
    for c in ports:
        if c.key == key:
            obj = c
    return obj


def main():
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.VM_NAME, cli.Argument.PORT_GROUP, cli.Argument.VM_MAC)
    args = parser.get_args()
    si = service_instance.connect(args)

    content = si.RetrieveContent()
    print("Search VDS PortGroup by Name ...")
    portgroup = pchelper.get_obj(content, [vim.dvs.DistributedVirtualPortgroup], args.port_group)
    if portgroup is None:
        print("Portgroup not Found in DVS ...")
        exit(0)
    print("Search Available(Unused) port for VM...")
    dvs = portgroup.config.distributedVirtualSwitch
    port_key = search_port(dvs, portgroup.key)
    port = port_find(dvs, port_key)
    print("Search VM by Name ...")
    vm = None
    vm = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)
    if vm:
        print("Find Vm , Add Nic Card ...")
        add_nic(vm, args.vm_mac, port)
    else:
        print("Vm not Found ...")


if __name__ == '__main__':
    sys.exit(main())
