#! /usr/bin/python3
#Jie Zheng(jiezheng@vmware.com)
"""
This script is to ease VM reconnection to dvportgroup in a batch style

"""
from pyVim.connect import SmartConnectNoSSL
from pyVmomi import vim
from pyVim import task as Task
import argparse


scaned_device_types = [
    vim.vm.device.VirtualE1000e,
    vim.vm.device.VirtualVmxnet3
]

saned_device_backing = [
   vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo 
]

def retrieve_vms(content):
    vm_view = content.viewManager.CreateContainerView(content.rootFolder,
        [vim.VirtualMachine],
        True)
    VMs = [vm for vm in vm_view.view]
    vm_view.Destroy()
    return VMs

def retrieve_network(content, pg_name):
    target_pg = None
    pg_view = content.viewManager.CreateContainerView(content.rootFolder,
        [vim.DistributedVirtualPortgroup],
        True)
    pgs = [pg for pg in pg_view.view]
    for pg in pgs:
        if pg.name == pg_name:
            target_pg = pg
            break
    if not target_pg:
        raise Exception("can not find the dvportgroup: %s" % (pg_name))
    return target_pg

def scan_disconnected_vnics(vm, pg):
    devices = []
    for dev in vm.config.hardware.device:
        if type(dev) not in scaned_device_types:
            continue
        if type(dev.backing) not in saned_device_backing:
            continue
        backing = dev.backing
        if backing.port.switchUuid != pg.config.distributedVirtualSwitch.uuid \
            or backing.port.portgroupKey != pg.config.key:
            continue
        if dev.connectable.connected == True:
            continue
        devices.append(dev)
    return devices


def migrate_device_to_VSS(vm, devs, vmnet = 'VM Network'):
    if not len(devs):
        return
    nic_changes = []
    for dev in devs:
        nic_change = vim.vm.device.VirtualDeviceSpec()
        nic_change.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        nic_change.device = type(dev)()
        nic_change.device.key = dev.key
        nic_change.device.deviceInfo = vim.Description()
        nic_change.device.deviceInfo.summary = 'refreshed by script'
        nic_change.device.backing = \
            vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
        nic_change.device.backing.deviceName = vmnet
        nic_change.device.connectable = \
            vim.vm.device.VirtualDevice.ConnectInfo()
        nic_change.device.connectable.status = 'ok'
        nic_change.device.connectable.startConnected = True
        nic_change.device.connectable.allowGuestControl = True
        nic_change.device.connectable.connected = True
        nic_change.device.resourceAllocation = \
            vim.vm.device.VirtualEthernetCard.ResourceAllocation()
        nic_change.device.resourceAllocation.reservation = \
            dev.resourceAllocation.reservation
        nic_change.device.resourceAllocation.limit = \
            dev.resourceAllocation.limit
        nic_change.device.resourceAllocation.share = vim.SharesInfo()
        nic_change.device.resourceAllocation.share.shares = \
            dev.resourceAllocation.share.shares
        nic_change.device.resourceAllocation.share.level = \
            dev.resourceAllocation.share.level
        nic_change.device.slotInfo = \
            vim.vm.device.VirtualDevice.PciBusSlotInfo()
        nic_change.device.slotInfo.pciSlotNumber = dev.slotInfo.pciSlotNumber
        nic_change.device.controllerKey = dev.controllerKey
        nic_change.device.unitNumber = dev.unitNumber
        nic_change.device.addressType = dev.addressType
        nic_change.device.macAddress = dev.macAddress
        nic_change.device.wakeOnLanEnabled = dev.wakeOnLanEnabled
        nic_change.device.externalId = dev.externalId
        nic_change.device.uptCompatibilityEnabled = dev.uptCompatibilityEnabled
        nic_changes.append(nic_change)
    spec = vim.vm.ConfigSpec()
    spec.deviceChange = nic_changes
    task = vm.ReconfigVM_Task(spec = spec)
    Task.WaitForTask(task = task)

def migrate_device_to_dvs(vm, devs, pg):
    if not len(devs):
        return
    nic_changes = []
    for dev in devs:
        nic_change = vim.vm.device.VirtualDeviceSpec()
        nic_change.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        nic_change.device = type(dev)()
        nic_change.device.key = dev.key
        nic_change.device.deviceInfo = vim.Description()
        nic_change.device.deviceInfo.summary = 'refreshed by script'
        nic_change.device.backing = \
          vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
        nic_change.device.backing.port = vim.dvs.PortConnection()
        nic_change.device.backing.port.switchUuid = \
            pg.config.distributedVirtualSwitch.uuid
        nic_change.device.backing.port.portgroupKey = pg.key
        nic_change.device.connectable = \
            vim.vm.device.VirtualDevice.ConnectInfo()
        nic_change.device.connectable.status = 'ok'
        nic_change.device.connectable.startConnected = True
        nic_change.device.connectable.allowGuestControl = True
        nic_change.device.connectable.connected = True
        nic_change.device.resourceAllocation = \
            vim.vm.device.VirtualEthernetCard.ResourceAllocation()
        nic_change.device.resourceAllocation.reservation = \
            dev.resourceAllocation.reservation
        nic_change.device.resourceAllocation.limit = \
            dev.resourceAllocation.limit
        nic_change.device.resourceAllocation.share = vim.SharesInfo()
        nic_change.device.resourceAllocation.share.shares = \
            dev.resourceAllocation.share.shares
        nic_change.device.resourceAllocation.share.level = \
            dev.resourceAllocation.share.level
        nic_change.device.slotInfo = \
            vim.vm.device.VirtualDevice.PciBusSlotInfo()
        nic_change.device.slotInfo.pciSlotNumber = dev.slotInfo.pciSlotNumber
        nic_change.device.controllerKey = dev.controllerKey
        nic_change.device.unitNumber = dev.unitNumber
        nic_change.device.addressType = dev.addressType
        nic_change.device.macAddress = dev.macAddress
        nic_change.device.wakeOnLanEnabled = dev.wakeOnLanEnabled
        nic_change.device.externalId = dev.externalId
        nic_change.device.uptCompatibilityEnabled = dev.uptCompatibilityEnabled
        nic_changes.append(nic_change)
    spec = vim.vm.ConfigSpec()
    spec.deviceChange = nic_changes
    task = vm.ReconfigVM_Task(spec = spec)
    Task.WaitForTask(task = task)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Process script arguments...')
    parser.add_argument('--host', type = str, required = True,
        help = 'the IP or name of the vSphere Center')
    parser.add_argument('--port', type = int, default = 443)
    parser.add_argument('--user', type = str, help = 'username',
        default = 'Administrator@vsphere.local')
    parser.add_argument('--pwd', type = str, help = 'password',
        default = 'Admin!23')
    parser.add_argument('--portgroup', type = str, required = True,
        help = 'the dvportgroup name')
    parser.add_argument('--interactive', default = False, required = False,
        action="store_true", help = 'interactive to process VM reconnection')
    args = parser.parse_args()
    return args

def main():
    args = parse_arguments()
    instance = SmartConnectNoSSL(host = args.host,
        user = args.user,
        pwd = args.pwd,
        port = args.port)
    content = instance.RetrieveContent()
    pg = retrieve_network(content, args.portgroup)
    print("Reconnect VMs connected to dvportgroup:%s dvs:%s" %
        (pg.name, pg.config.distributedVirtualSwitch.name))
    vms = retrieve_vms(content)
    for vm in vms:
        devs = scan_disconnected_vnics(vm, pg)
        if not len(devs):
            continue
        if not args.interactive:
            print("Ready to reconnect VM:(%s) vnic:%s" %
                (vm.name, [dev.key for dev in devs]))
        else:
            proceed = False
            while True:
                choice = input("Ready to reconnect VM:(%s) vnic:%s (y/n):" %
                    (vm.name, [dev.key for dev in devs]))
                if choice == 'y':
                    proceed = True
                elif choice == 'n':
                    proceed = False
                else:
                    continue
                break
            if not proceed:
                continue
        try:
            migrate_device_to_VSS(vm, devs)
            migrate_device_to_dvs(vm, devs, pg)
        except Exception as e:
            print('Reconnecting VM:(%s) fails, please process it mannually' %
                (vm.name))

if __name__ == '__main__':
    main()
