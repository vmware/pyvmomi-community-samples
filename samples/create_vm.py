#!/usr/bin/env python
# Alexander Todorov <atodorov@redhat.com>

"""
Create a VM with an existing .vmdk file attached as IDE 0 disk
and power it on.
"""
from __future__ import print_function

import ssl
import atexit

from pyVim import connect
from pyVmomi import vim

from tools import cli
from tools import tasks


def get_args():
    """
    Use the tools.cli methods and then add a few more arguments.
    """
    parser = cli.build_arg_parser()

    parser.add_argument('--datacenter',
                        required=True,
                        action='store',
                        help='Name of data center to create VM in')

    parser.add_argument('-c', '--cluster',
                        required=True,
                        action='store',
                        help='Name of resource cluster')

    parser.add_argument('-f', '--folder',
                        required=True,
                        action='store',
                        help='Name of inventory folder in which to create VM')

    parser.add_argument('-d', '--datastore',
                        required=True,
                        action='store',
                        help='Name of Datastore where vmdk file is')

    parser.add_argument('--portgroup',
                        required=False,
                        action='store',
                        help='Network portgroup name')

    parser.add_argument('-v', '--vmdk-file',
                        required=True,
                        action='store',
                        help='Path on datastore to .vmdk file')

    parser.add_argument('-n', '--name',
                        required=True,
                        action='store',
                        help='Name of VM to create')

    parser.add_argument('-m', '--memory',
                        type=int,
                        required=True,
                        action='store',
                        help='Memory in MB')

    parser.add_argument('-g', '--guest_type',
                        required=True,
                        action='store',
                        help='VM guest type')

    parser.add_argument('--power-on',
                        dest='power_on',
                        required=False,
                        default=False,
                        action='store_true',
                        help='Power on the VM after creation')

    args = parser.parse_args()

    return cli.prompt_for_password(args)


def search_port(dvs, portgroupkey):
    search_portkey = []
    criteria = vim.dvs.PortCriteria()
    criteria.connected = False
    criteria.inside = True
    criteria.portgroupKey = portgroupkey
    ports = dvs.FetchDVPorts(criteria)
    for port in ports:
        search_portkey.append(port.key)
    return search_portkey[0]


def port_find(dvs, key):
    obj = None
    ports = dvs.FetchDVPorts()
    for c in ports:
        if c.key == key:
            obj = c
    return obj


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


def create_vm(vm_name, vmdk_path, vm_ram, vm_guest, power_on, portgroup,
              service_instance, data_store, data_center, vm_folder,
              resource_pool):
    """Creates a VirtualMachine.

    :param vm_name: String Name for the VirtualMachine
    :param vmdk_path: Full path to vmdk file in the datastore
    :param vm_ram: Memory in MB
    :param vm_guest: Guest type, e.g. rhel7_64Guest
    :param power_on: Boolean
    :param portgroup: Network port group to attach the NIC to
    :param service_instance: ServiceInstance connection
    :param data_store: DataStore to place the VirtualMachine on
    :param data_center: DataCenter hosting the VirtualMachine
    :param vm_folder: Folder to place the VirtualMachine in
    :param resource_pool: ResourcePool to place the VirtualMachine in
    """
    # bare minimum VM shell, no disks.
    vmx_path = '[' + data_store.info.name + '] ' + vm_name + '.vmx'
    vmx_file = vim.vm.FileInfo(logDirectory=None,
                               snapshotDirectory=None,
                               suspendDirectory=None,
                               vmPathName=vmx_path)

    # config for VM
    config = vim.vm.ConfigSpec(name=vm_name, memoryMB=vm_ram, numCPUs=1,
                               files=vmx_file, guestId=vm_guest,
                               version='vmx-13')

    task = vm_folder.CreateVM_Task(config=config, pool=resource_pool)
    tasks.wait_for_tasks(service_instance, [task])

    vm = get_obj(service_instance.RetrieveContent(),
                 [vim.VirtualMachine],
                 vm_name)
    if not vm:
        raise Exception('Virtual machine %s not created' % vm_name)

    # find IDE 0 controller to attach disk to
    controller = None
    for dev in vm.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualIDEController) and \
           dev.deviceInfo.label == 'IDE 0':
            controller = dev
            break

    if not controller:
        raise Exception('IDE 0 controller not found')

    disk_spec = vim.vm.device.VirtualDeviceSpec(
        device=vim.vm.device.VirtualDisk(
            unitNumber=0,
            controllerKey=controller.key,
            backing=vim.vm.device.VirtualDisk.FlatVer2BackingInfo(
                datastore=data_store,
                fileName=vmdk_path,
                diskMode='persistent',
            ),
        ),
        operation=vim.vm.device.VirtualDeviceSpec.Operation.add)

    spec = vim.vm.ConfigSpec()
    spec.deviceChange = [disk_spec]

    if portgroup:
        dvs = portgroup.config.distributedVirtualSwitch
        portKey = search_port(dvs, portgroup.key)
        port = port_find(dvs, portKey)

        # network backing config
        VirtualEthernetCard = vim.vm.device.VirtualEthernetCard
        bk = VirtualEthernetCard.DistributedVirtualPortBackingInfo(
            port=vim.dvs.PortConnection(
                portgroupKey=port.portgroupKey,
                switchUuid=port.dvsUuid,
                portKey=port.key,
            ),
        )

        nic_spec = vim.vm.device.VirtualDeviceSpec(
            operation=vim.vm.device.VirtualDeviceSpec.Operation.add,
            device=vim.vm.device.VirtualVmxnet3(
                key=0,
                deviceInfo=vim.Description(summary='vCenter API test'),
                backing=bk,
                connectable=vim.vm.device.VirtualDevice.ConnectInfo(
                    startConnected=True,
                    allowGuestControl=True,
                    connected=True,
                    status='ok',
                ),
                wakeOnLanEnabled=True,
                addressType='assigned',
            ),
        )

        spec.deviceChange.append(nic_spec)

    task = vm.ReconfigVM_Task(spec=spec)
    tasks.wait_for_tasks(service_instance, [task])

    if power_on:
        task = data_center.PowerOnMultiVM_Task([vm])
        tasks.wait_for_tasks(service_instance, [task])

    print(vm.summary.config.instanceUuid)


def main():
    args = get_args()

    sslContext = None

    if args.disable_ssl_verification:
        sslContext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        sslContext.verify_mode = ssl.CERT_NONE

    service_instance = connect.SmartConnect(host=args.host,
                                            user=args.user,
                                            pwd=args.password,
                                            port=int(args.port),
                                            sslContext=sslContext)
    if not service_instance:
        raise Exception("Could not connect to the specified host")

    atexit.register(connect.Disconnect, service_instance)

    content = service_instance.RetrieveContent()

    # find the datacenter we are using
    datacenter = get_obj(content, [vim.Datacenter], args.datacenter)
    if not datacenter:
        raise Exception('Datacenter %s not found' % args.datacenter)

    # find the computing resource cluster
    cluster = get_obj(content, [vim.ClusterComputeResource], args.cluster)
    if not cluster:
        raise Exception('Resource cluster %s not found' % args.cluster)

    # find inventory folder in which to create VM
    vmfolder = get_obj(content, [vim.Folder], args.folder)
    if not vmfolder:
        raise Exception('Inventory folder %s not found' % args.folder)

    # find datastore which contains the vmdk file
    datastore = get_obj(content, [vim.Datastore], args.datastore)
    if not datastore:
        raise Exception('Datastore %s not found' % args.datastore)

    # find the network to attach to
    portgroup = None
    if args.portgroup:
        portgroup = get_obj(content,
                            [vim.dvs.DistributedVirtualPortgroup],
                            args.portgroup)
        if not portgroup:
            raise Exception('Portgroup %s not found' % args.portgroup)

    vmdk_path = '[' + args.datastore + '] ' + args.vmdk_file
    create_vm(args.name, vmdk_path, args.memory, args.guest_type,
              args.power_on,
              portgroup, service_instance, datastore, datacenter, vmfolder,
              cluster.resourcePool)

# Start program
if __name__ == "__main__":
    main()
