# Written by Mahesh kumar and Pavan Bidkar
# GitHub: https://github.com/vmware/pyvmomi
# Email: kumahesh@vmware.com, pbidkar@vmware.com
#
# This code has been released under the terms of the Apache-2.0 license
# http://opensource.org/licenses/Apache-2.0
#
# Description: This sample relocates vm to the target esx host across clusters,
# datastore and datacenter
#

import atexit

from pyVim.connect import Disconnect, SmartConnectNoSSL, SmartConnect
from pyVmomi import vim, vmodl

from tools import cli


def get_args():
    """
    Adds additional args for the vMotion
    """
    parser = cli.build_arg_parser()

    parser.add_argument('-dd', '--datastore-dest',
                        required=False,
                        help=' Datastore of the destination')

    parser.add_argument('-t', '--target-esx-host',
                        required=False,
                        help="name of the destination esx host")

    parser.add_argument('-v', '--vm-name',
                        required=True,
                        help="name of the vm")
    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)


def get_object(content, vimtype, name, disp=False):
    """
    Internal method to create objects of various vCenter related classes
    :param content:
    :param vimtype:
    :param name:
    :return: Object
    """
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder,
                                                        vimtype,
                                                        True)
    for c in container.view:
        if disp:
            print("c.name:" + str(c.name))
        if c.name == name:
            obj = c
            break
    return obj


def collect_template_disks(vm):
    """
        Internal method to collect template disks
        :param vm: VM object
        :return: list of template disks
    """
    template_disks = []
    for device in vm.config.hardware.device:
        if type(device).__name__ == "vim.vm.device.VirtualDisk":
            datastore = device.backing.datastore
            print("device.deviceInfo.summary:" + device.deviceInfo.summary)
            print("datastore.summary.type:" + datastore.summary.type)
            if hasattr(device.backing, 'fileName'):
                disk_desc = str(device.backing.fileName)
                print("Disc Discription -- {}".format(disk_desc))
                drive = disk_desc.split("]")[0].replace("[", "")
                print("drive:" + drive)
                print("device.backing.fileName:" + device.backing.fileName)
                template_disks.append(device)
    return template_disks


def construct_locator(template_disks, datastore_dest_id):
    """
        Internal method to construct locator for the disks
        :param template_disks: list of template_disks
        :param datastore_dest_id: ID of destination datastore
        :return: locator
    """
    ds_disk = []
    for index, wdisk in enumerate(template_disks):
        print("relocate index:" + str(index))
        print("disk:" + str(wdisk))
        disk_desc = str(wdisk.backing.fileName)
        drive = disk_desc.split("]")[0].replace("[", "")
        print("drive:" + drive)
        print("wdisk.backing.fileName:" + wdisk.backing.fileName)
        locator = vim.vm.RelocateSpec.DiskLocator()
        locator.diskBackingInfo = wdisk.backing
        locator.diskId = int(wdisk.key)
        locator.datastore = datastore_dest_id
        ds_disk.append(locator)
    return ds_disk


def relocate_vm(vm_name, content, host_dest, datastore_dest=None, **kwargs):
    """
    This method relocates vm to the host_dest across
    datacenters, clusters, datastores managed by a Vcenter

    Args:
        vm_name:
        vcenter:
        host_dest:
        datastore_src
        datastore_dest:
        **kwargs:

    Returns:

    """
    relocation_status = False
    message = "relocate_vm passed"
    try:
        vm = get_object(content, [vim.VirtualMachine], vm_name)
        current_host = vm.runtime.host.name
        print("vmotion_vm current_host:" + current_host)

        # Create Relocate Spec
        spec = vim.VirtualMachineRelocateSpec()

        # Check whether compute vmotion required and construct spec accordingly
        if host_dest is not None:
            if current_host == host_dest:
                raise Exception("WARNING:: destination_host can not equal "
                                "current_host")

            # Find destination host
            destination_host = get_object(content, [vim.HostSystem], host_dest)
            print("vmotion_vm destination_host:" + str(destination_host))
            spec.host = destination_host

            # Find destination Resource pool
            resource_pool = destination_host.parent.resourcePool
            print("vmotion_vm resource_pool:" + str(resource_pool))
            spec.pool = resource_pool

        # Check whether storage vmotion required and construct spec accordingly
        if datastore_dest is not None:
            # collect disks belong to the VM
            template_disks = collect_template_disks(vm)
            datastore_dest_id = get_object(content,
                                           [vim.Datastore],
                                           datastore_dest)
            spec.datastore = datastore_dest_id
            spec.disk = construct_locator(template_disks, datastore_dest_id)

        print("relocate_vm spec:" + str(spec))
        task = vm.RelocateVM_Task(spec)
        while task.info.state == vim.TaskInfo.State.running:
            continue
        relocation_status = True
    except Exception as e:
        message = "relocate_vm failed for vm:" + vm_name \
                  + " with error:" + str(e)
    print(message)
    return relocation_status, message


def main():

    args = get_args()

    try:
        if args.disable_ssl_verification:
            service_instance = SmartConnectNoSSL(host=args.host,
                                                 user=args.user,
                                                 pwd=args.password,
                                                 port=args.port)
        else:
            service_instance = SmartConnect(host=args.host,
                                            user=args.user,
                                            pwd=args.password,
                                            port=args.port)

        atexit.register(Disconnect, service_instance)

        content = service_instance.RetrieveContent()

        # Assigning destination datastores
        datastore_dest = args.datastore_dest

        # Target compute resource
        host_dest = args.target_esx_host

        relocate_vm(args.vm_name,
                    content=content,
                    host_dest=host_dest,
                    datastore_dest=datastore_dest)

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
