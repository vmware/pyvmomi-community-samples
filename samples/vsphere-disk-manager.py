#!/usr/bin/env python

"""
Written by Miquel Adrover
https://github.com/madrover

Forked and extended from https://github.com/vmware/pyvmomi-community-samples/blob/master/samples/add_disk_to_vm.py

Script to manage independent disks on vSphere.

The following disk operations are available:
- add
- attach
- detach
- list
- destroy

Known issues:
This will not add more than 15 disks to a VM
To do that the VM needs an additional scsi controller
and I have not yet worked through that
"""

from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
import atexit
import argparse
import getpass
import ssl
import sys
import time


def get_args():
    parser = argparse.ArgumentParser(
        description='Disk manager for vSphere')

    parser.add_argument('--operation',
                        required=True,
                        action='store',
                        choices=['add', 'attach', 'detach', 'list', 'destroy'],
                        default='add',
                        help='Operation to execute')

    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='vSphere server')
    parser.add_argument('-o', '--port',
                        type=int,
                        default=443,
                        action='store',
                        help='vSphere port')

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='Username')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password')

    parser.add_argument('-v', '--vm-name',
                        required=False,
                        action='store',
                        help='name of the vm')

    parser.add_argument('--uuid',
                        required=False,
                        action='store',
                        help='vmuuid of vm')

    parser.add_argument('--disk-type',
                        required=False,
                        action='store',
                        default='thin',
                        choices=['thick', 'thin'],
                        help='thick or thin')

    parser.add_argument('--data-store',
                        required=False,
                        action='store',
                        help='disk data-store')

    parser.add_argument('--disk-size',
                        required=False,
                        action='store',
                        help='disk size, in GB, to add to the VM')

    parser.add_argument('--disk-path',
                        required=False,
                        action='store',
                        help='disk path')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password')

    return args


def get_obj(connection, vimtype, name):
    content = connection.RetrieveContent()
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def connect(args):
    # Create SSL context that doesn't check SSL certificates
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print "Connecting to vSphere"
    connection = SmartConnect(
        host=args.host,
        user=args.user,
        pwd=args.password,
        port=args.port,
        sslContext=ctx)
    # Disconnect on exit
    atexit.register(Disconnect, connection)
    print "Connected"
    return connection


def get_vm(args, connection):
    vm = None
    if args.uuid:
        search_index = connection.content.searchIndex
        vm = search_index.FindByUuid(None, args.uuid, True)
    elif args.vm_name:
        vm = get_obj(connection, [vim.VirtualMachine], args.vm_name)
    if vm:
        print 'VM: ' + vm.config.name
    else:
        print "VM not found"
        sys.exit(1)
    return vm


# Get all disks and controller on a VM
# Find available unit slot on the controller
def get_devices(vm):
    available_unit_slot = 0
    disks = []
    for dev in vm.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualDisk) and \
           hasattr(dev.backing, 'fileName'):
            print '- ' + dev.backing.fileName
            disks.append(dev)
            available_unit_slot = int(dev.unitNumber) + 1
            # available_unit_slot 7 reserved for scsi controller
            if available_unit_slot == 7:
                available_unit_slot += 1
            if available_unit_slot >= 16:
                print "we don't support this many disks"
                return
        elif isinstance(dev, vim.vm.device.VirtualSCSIController):
            print '- ' + dev.deviceInfo.label
            controller = dev
    print 'Available unit slot: ' + str(available_unit_slot)
    return controller, available_unit_slot, disks


def add_disk(connection, vm, controller, available_unit_slot, data_store,
             disk_path, disk_size, disk_type):
    print "Adding %sGB disk to %s" % (disk_size, vm.config.name)
    spec = vim.vm.ConfigSpec()
    dev_changes = []
    disk_spec = vim.vm.device.VirtualDeviceSpec()
    new_disk_kb = int(disk_size) * 1024 * 1024
    disk_spec.fileOperation = "create"
    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    disk_spec.device = vim.vm.device.VirtualDisk()
    disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
    if disk_type == 'thin':
        disk_spec.device.backing.thinProvisioned = True
    disk_spec.device.backing.diskMode = 'persistent'
    if data_store is not None and disk_path is not None:
        disk_spec.device.backing.fileName = '[' + data_store + '] ' + disk_path
        disk_spec.device.backing.fileName = '[' + data_store + '] ' + disk_path
        disk_spec.device.backing.datastore = get_obj(connection,
                                                     [vim.Datastore],
                                                     data_store)
    disk_spec.device.unitNumber = available_unit_slot
    disk_spec.device.capacityInKB = new_disk_kb
    disk_spec.device.controllerKey = controller.key
    disk_spec.fileOperation = "create"
    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    dev_changes.append(disk_spec)
    spec.deviceChange = dev_changes
    task = vm.ReconfigVM_Task(spec=spec)
    wait_for_task(task, connection)
    print "%sGB disk added to %s" % (disk_size, vm.config.name)


def detach_disk(connection, vm, disks, data_store, disk_path, destroy=False):
    detached_disk = None
    disk_path = '[' + data_store + '] ' + disk_path
    if destroy:
        print 'Destroying disk: ' + disk_path
    else:
        print 'Detaching disk: ' + disk_path
    for d in disks:
        if d.backing.fileName == disk_path:
            detached_disk = d
    if not detached_disk:
        print disk_path + ' not attached'
        sys.exit(1)
    disk_spec = vim.vm.device.VirtualDeviceSpec()
    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
    if destroy:
        disk_spec.fileOperation = \
            vim.vm.device.VirtualDeviceSpec.FileOperation.destroy
    disk_spec.device = detached_disk
    spec = vim.vm.ConfigSpec()
    spec.deviceChange = [disk_spec]
    task = vm.ReconfigVM_Task(spec=spec)
    wait_for_task(task, connection)
    if destroy:
        print 'Disk destroyed'
    else:
        print 'Disk detached'


def destroy_disk(connection, vm, disks, data_store, disk_path):
    detach_disk(connection, vm, disks, data_store, disk_path, True)


def attach_disk(connection, vm, controller, available_unit_slot,
                data_store, disk_path):
    print "Attaching [%s] %s" % (data_store, disk_path)
    spec = vim.vm.ConfigSpec()
    dev_changes = []
    disk_spec = vim.vm.device.VirtualDeviceSpec()
    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    disk_spec.device = vim.vm.device.VirtualDisk()
    disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
    disk_spec.device.backing.fileName = '[' + data_store + '] ' + disk_path
    disk_spec.device.backing.diskMode = 'persistent'
    disk_spec.device.backing.datastore = get_obj(connection, [vim.Datastore],
                                                 data_store)
    disk_spec.device.unitNumber = available_unit_slot
    disk_spec.device.controllerKey = controller.key
    dev_changes.append(disk_spec)
    spec.deviceChange = dev_changes
    task = vm.ReconfigVM_Task(spec=spec)
    wait_for_task(task, connection)


def wait_for_task(task, actionName='job', hideResult=False):
    """
    Waits and provides updates on a vSphere task
    """
    while task.info.state == vim.TaskInfo.State.running:
        time.sleep(2)

        if task.info.state == vim.TaskInfo.State.success:
            if task.info.result is not None and not hideResult:
                out = '%s completed successfully, result: %s' % \
                    (actionName, task.info.result)
                print out
            else:
                out = '%s completed successfully.' % actionName
                print out
        else:
            out = '%s did not complete successfully: %s' % \
                (actionName, task.info.error)
            raise task.info.error
            print out

    return task.info.result


def main():
    args = get_args()
    connection = connect(args)
    vm = get_vm(args, connection)
    print 'Devices:'
    controller, available_unit_slot, disks = get_devices(vm)
    if args.operation == 'add':
        add_disk(connection, vm, controller, available_unit_slot,
                 args.data_store, args.disk_path, args.disk_size,
                 args.disk_type)
    elif args.operation == 'attach':
        attach_disk(connection, vm, controller, available_unit_slot,
                    args.data_store, args.disk_path)
    elif args.operation == 'detach':
        detach_disk(connection, vm, disks, args.data_store, args.disk_path)
    elif args.operation == 'destroy':
        destroy_disk(connection, vm, disks, args.data_store, args.disk_path)
    if args.operation != 'list':
        print 'Updated devices:'
        get_devices(vm)


if __name__ == "__main__":
    main()
