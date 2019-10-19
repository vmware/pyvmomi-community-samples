#!/usr/bin/env python


#pyvmomi script to make existing VMDK disk as FCD
#author : Chandan Hegde (chandanhegden@gmail.com) https://github.com/Chandan-Hegde

from __future__ import print_function

from pyVmomi import vim
from tools import tasks
import argparse
import getpass
from pyVim.connect import SmartConnectNoSSL, Disconnect
import atexit
import sys


def get_args():
    """Get command line args from the user.
    """
    parser = argparse.ArgumentParser(
        description='Standard Arguments for talking to vCenter')

    # because -h is reserved for 'help' we use -s for service
    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='vSphere service to connect to')

    # because we want -p for password, we use -o for port
    parser.add_argument('-o', '--port',
                        type=int,
                        default=443,
                        action='store',
                        help='Port to connect on')

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='User name to use when connecting to host')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to use when connecting to host')
    parser.add_argument('-v', '--vmname', required=True,
                        help='Name of the VirtualMachine you want to change.')
    parser.add_argument('-d', '--disk-number', required=True,
                        help='Disk number to change mode.')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password for host %s and user %s: ' %
                   (args.host, args.user))
    return args


def get_obj(content, vim_type, name):
    obj = None

    container = content.viewManager.CreateContainerView(content.rootFolder, vim_type, True)

    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def build_paramters(si, ds, vm, vmdk_file, vc_name):

    l = vmdk_file.split("/")
    path_parameter = "https://" + vc_name + "/folder/" + vm + "/" + l[len(l)-1] + "?dcPath=prme-Vgrid&dsName=" + ds
    return path_parameter


#Module to promote the virtual disk as FCD
def mkfcd(vc_name, si, content, vm_obj, disk_number, disk_prefix_label='Hard disk '):

    disk_label = disk_prefix_label + str(disk_number)
    virtual_disk_device = None

    # find the disk device
    for dev in vm_obj.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualDisk) and dev.deviceInfo.label == disk_label:
            virtual_disk_device = dev

    # if virtual disk is not found
    if not virtual_disk_device:
        raise RuntimeError("##Virtual {} could not be found".format(disk_label))

    # checkigng the disk details
    if hasattr(virtual_disk_device.backing, 'fileName'):
        datastore = virtual_disk_device.backing.datastore
        if datastore:
            summary = {'capacity': datastore.summary.capacity,
                       'freeSpace': datastore.summary.freeSpace,
                       'file system': datastore.summary.type,
                       'url': datastore.summary.url}
            for key, val in summary.items():
                if key == 'url':
                    path_to_disk = val



        path_to_disk += virtual_disk_device.backing.fileName
        parameter_for_fcd_disk = build_paramters(si, datastore.name, vm_obj.name, virtual_disk_device.backing.fileName, vc_name)

        #Registewring the disk as first class
        vstorage = content.vStorageObjectManager.RegisterDisk(parameter_for_fcd_disk)

        print("##The id is %s" % vstorage.config.id.id )

        print("##The data store MOID is %s" % vstorage.config. backing.datastore )


        #keeping last annotation as a buffer
        previous_annotation = vm_obj.summary.config.annotation

        #setting annotation
        spec = vim.vm.ConfigSpec()
        spec.annotation = previous_annotation + "Disk"+str(disk_number) + ":" + str(vstorage.config.id.id) + "\n"
        task=vm_obj.ReconfigVM_Task(spec)
        tasks.wait_for_tasks(si,[task])
        print("##Added the id annotation to VM")

    return True


def main():
    args = get_args()
    si = SmartConnectNoSSL(host=args.host,
                           user=args.user,
                           pwd=args.password,
                           port=int(args.port))
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()
    print("##Searching for VM %s" % args.vmname)
    vm_obj = get_obj(content, [vim.VirtualMachine], args.vmname)

    try:
        if vm_obj:
            fcd_task = mkfcd(args.host, si, content, vm_obj, args.disk_number)
            print("##The Hard Disk %s is promoted to FCD" % args.disk_number)
    except Exception as e:
        print("##Exception in making disk as FCD %s" % e)


if __name__ == "__main__":
    main()

