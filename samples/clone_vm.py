#!/usr/bin/env python
"""
Written by Dann Bohn
Github: https://github.com/whereismyjetpack
Email: dannbohn@gmail.com

Clone a VM from template example
"""
from pyVmomi import vim
from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect
import atexit
import argparse
import getpass

from add_nic_to_vm import add_nic


SUCCESS = True
FAILURE = False


def get_args():
    """ Get arguments from CLI """
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
                        help='Username to use')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to use')

    parser.add_argument('-v', '--vm-name',
                        required=True,
                        action='store',
                        help='Name of the VM you wish to make')

    parser.add_argument('--no-ssl',
                        action='store_true',
                        help='Skip SSL verification')

    parser.add_argument('--template',
                        required=True,
                        action='store',
                        help='Name of the template/VM \
                            you are cloning from')

    parser.add_argument('--datacenter-name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the Datacenter you\
                            wish to use. If omitted, the first\
                            datacenter will be used.')

    parser.add_argument('--vm-folder',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the VMFolder you wish\
                            the VM to be dumped in. If left blank\
                            The datacenter VM folder will be used')

    parser.add_argument('--datastore-name',
                        required=False,
                        action='store',
                        default=None,
                        help='Datastore you wish the VM to end up on\
                            If left blank, VM will be put on the same \
                            datastore as the template')

    parser.add_argument('--datastorecluster-name',
                        required=False,
                        action='store',
                        default=None,
                        help='Datastorecluster (DRS Storagepod) you wish '
                             'the VM to end up on Will override the '
                             'datastore-name parameter.')

    parser.add_argument('--cluster-name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the cluster you wish the VM to\
                            end up on. If left blank the first cluster found\
                            will be used')

    parser.add_argument('--resource-pool',
                        required=False,
                        action='store',
                        default=None,
                        help='Resource Pool to use. If left blank the first\
                            resource pool found will be used')

    parser.add_argument('--power-on',
                        dest='power_on',
                        action='store_true',
                        help='power on the VM after creation')

    parser.add_argument('--opaque-network',
                        required=False,
                        help='Name of the opaque network to add to the VM')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password')

    return args


def wait_for_task(task):
    """ wait for a vCenter task to finish """
    while True:
        if task.info.state == 'success':
            return task.info.result

        if task.info.state == 'error':
            print("there was an error")
            return FAILURE


def get_obj(content, vimtype, name, datacenter=None):
    """
    Return an object by name, if name is None the
    first found object is returned
    """
    obj = None
    if datacenter is None:
        container = content.viewManager.CreateContainerView(
            content.rootFolder, vimtype, True)
    else:
        container = content.viewManager.CreateContainerView(
            datacenter, vimtype, True)
    for c in container.view:
        if name:
            if c.name == name:
                obj = c
                break
        else:
            obj = c
            break

    return obj


def clone_vm(
        content, template, vm_name,
        datacenter_name, vm_folder_name, datastore_name,
        cluster_name, resource_pool_name, power_on, datastorecluster_name):
    """
    Clone a VM from a template/VM, datacenter_name, vm_folder, datastore_name
    cluster_name, resource_pool, and power_on are all optional.
    """

    # if none git the first one
    datacenter = get_obj(content, [vim.Datacenter], datacenter_name)

    if vm_folder_name:
        destfolder = get_obj(content, [vim.Folder], vm_folder_name,
                             datacenter=datacenter)
    else:
        destfolder = datacenter.vmFolder

    # if None, get the first one
    cluster = get_obj(content, [vim.ClusterComputeResource], cluster_name,
                      datacenter=datacenter)

    resource_pool = None
    if resource_pool_name:
        resource_pool = get_obj(content, [vim.ResourcePool],
                                resource_pool_name,
                                datacenter=datacenter)
    elif cluster:  # if cluster is not none, take it from there
        resource_pool = cluster.resourcePool

    if resource_pool is None:
        print("Not able to find resource pool for cloning VM")
        return FAILURE

    vmconf = vim.vm.ConfigSpec()

    if datastorecluster_name:
        podsel = vim.storageDrs.PodSelectionSpec()
        pod = get_obj(content, [vim.StoragePod], datastorecluster_name,
                      datacenter=datacenter)
        podsel.storagePod = pod

        storagespec = vim.storageDrs.StoragePlacementSpec()
        storagespec.podSelectionSpec = podsel
        storagespec.type = 'create'
        storagespec.folder = destfolder
        storagespec.resourcePool = resource_pool
        storagespec.configSpec = vmconf

        try:
            rec = content.storageResourceManager.RecommendDatastores(
                storageSpec=storagespec)
            rec_action = rec.recommendations[0].action[0]
            real_datastore_name = rec_action.destination.name
        except Exception:
            real_datastore_name = template.datastore[0].info.name

    elif datastore_name:
        real_datastore_name = datastore_name
    else:
        real_datastore_name = template.datastore[0].info.name

    datastore = get_obj(content, [vim.Datastore], real_datastore_name,
                        datacenter=datacenter)
    if datastore is None:
        print("Not able to find datastore for cloning vm")
        return FAILURE

    # set relospec
    relospec = vim.vm.RelocateSpec()
    relospec.datastore = datastore
    relospec.pool = resource_pool

    clonespec = vim.vm.CloneSpec()
    clonespec.location = relospec
    clonespec.powerOn = power_on

    print("cloning VM...")
    task = template.Clone(folder=destfolder, name=vm_name, spec=clonespec)
    return wait_for_task(task)


def main():
    """
    Let this thing fly
    """
    args = get_args()

    # connect this thing
    if args.no_ssl:
        si = SmartConnectNoSSL(
            host=args.host,
            user=args.user,
            pwd=args.password,
            port=args.port)
    else:
        si = SmartConnect(
            host=args.host,
            user=args.user,
            pwd=args.password,
            port=args.port)
    # disconnect this thing
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()

    template = get_obj(content, [vim.VirtualMachine], args.template)

    if template:
        status = clone_vm(
            content, template, args.vm_name,
            args.datacenter_name, args.vm_folder,
            args.datastore_name, args.cluster_name,
            args.resource_pool, args.power_on, args.datastorecluster_name)
        if status and args.opaque_network:
            vm = get_obj(content, [vim.VirtualMachine], args.vm_name)
            add_nic(si, vm, args.opaque_network)
    else:
        print("template not found")


# start this thing
if __name__ == "__main__":
    main()
