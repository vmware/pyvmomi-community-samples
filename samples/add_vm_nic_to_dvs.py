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
    print "Nic card added success ..."


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
    print search_portkey
    return search_portkey[0]


def get_args():
    if len(sys.argv) > 1:
        host, user, password, vm_name,port_group, macAddress = sys.argv[1:]
    else:
        host = raw_input("Vcenter IP : ")
        user = raw_input("User: ")
        password = raw_input("Password: ")
        vm_name = raw_input("VM_name: ")
        port_group = raw_input("Port_Group: ")
        macAddress = raw_input("Input MacAddress :")
    return host, user, password, vm_name, port_group, macAddress


def port_find(dvs, key):
    obj = None
    ports = dvs.FetchDVPorts()
    for c in ports:
        if c.key == key:
            obj = c
    return obj


def main():
    host, user, password, vm_name, port_group, macAddress = get_args()
    default_port = "443"
    serviceInstance = SmartConnect(host = host,
                                   user = user,
                                   pwd = password,
                                   port = default_port)
    atexit.register(Disconnect, serviceInstance)
    content = serviceInstance.RetrieveContent()
    print "Search VDS PortGroup by Name ..."
    portgroup = None
    portgroup = get_obj(content,
                        [vim.dvs.DistributedVirtualPortgroup], port_group)
    if portgroup is None:
        print "Portgroup not Found in DVS ..."
        exit(0)
    print "Search Available(Unused) port for VM..."
    dvs = portgroup.config.distributedVirtualSwitch
    portKey = search_port(dvs,portgroup.key)
    port = port_find(dvs, portKey)
    print "Search VM by Name ..."
    vm = None
    vm = get_obj(content, [vim.VirtualMachine], vm_name)
    if vm:
        print "Find Vm , Add Nic Card ..."
        add_nic(vm, macAddress, port)
    else:
        print "Vm not Found ..."


if __name__ == '__main__':
    sys.exit(main())