#!/usr/bin/env python
#
# Written by Mahesh kumar
# GitHub:   https://github.com/kumahesh
# Email:    kumahesh@vmware.com
# Description: This sample creates basic virtual machine
# taking host, datastore and folder as parameters
#
# Prerequisite: Folder of type 'VirtualMachine' has to be created
# if not already present
#
# This code has been released under the terms of the Apache-2.0 license
# http://opensource.org/licenses/Apache-2.0
#
import atexit

from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim

from tools import cli
from tools.pchelper import get_container_view
from tools import vm
from tools.tasks import wait_for_tasks


class ObjectNotFoundError(Exception):
    def __init__(self, message, *args, **kwargs):
        self.message = message
        Exception.__init__(self, *args, **kwargs)


def get_obj(si, vimtype, name):
    obj = None
    container = get_container_view(si, vimtype)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def get_args():
    parser = cli.build_arg_parser()

    parser.add_argument('--vm-name', required=True,
                        help="Name of the VirtualMachine to create.")
    parser.add_argument('--host-name', required=True,
                        help="Name of the host where vm will reside")
    parser.add_argument('--datastore-name', required=False,
                        help="Name of the datastore if not given, first "
                             "first datastore of host will be taken")
    parser.add_argument('--folder-name', required=True,
                        help="Name of the folder which will carry the vm")
    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)


def create_basic_vm(service_instance, vm_name, host_name,
                    folder_name, datastore_name=None):

    def check_for_none(x, error_message="Object not found"):
        if x is None:
            raise ObjectNotFoundError(error_message)
        return x

    try:
        # construct the spec
        spec = vim.vm.ConfigSpec()
        spec.alternateGuestName = "vm for test purpose"
        spec.name = vm_name
        spec.files = vim.vm.FileInfo()

        folder = check_for_none(get_obj(service_instance, [vim.Folder],
                                        folder_name), "Folder not found")
        host = check_for_none(get_obj(service_instance, [vim.HostSystem],
                                      host_name), "Host not found")

        if not datastore_name:
            if len(host.datastore) == 0:
                raise ObjectNotFoundError("Host do not have any datastore")
            datastore_name = host.datastore[0].summary.name

        spec.files.vmPathName = '[' + datastore_name + ']' + vm_name
        # Get available compute resources
        objview = get_container_view(service_instance, [vim.ComputeResource])
        compute_pools = objview.view
        objview.Destroy()

        # find the matching resource pool
        for compute_pool in compute_pools:
            if host in compute_pool.host:
                resource_pool = compute_pool.resourcePool

        # call create_VM on the folder
        tasks = [folder.CreateVM_Task(spec, resource_pool, host)]
        wait_for_tasks(service_instance, tasks)
    except ObjectNotFoundError as e:
        print(e.message)


def main():
    """
    Simple command-line program for listing the virtual machines on a system.
    """

    args = get_args()

    try:
        if args.disable_ssl_verification:
            # Connect to server without using SSL certificate verification
            service_instance = connect.SmartConnectNoSSL(host=args.host,
                                                         user=args.user,
                                                         pwd=args.password,
                                                         port=args.port)
        else:
            service_instance = connect.SmartConnect(host=args.host,
                                                    user=args.user,
                                                    pwd=args.password,
                                                    port=args.port)

        if not service_instance:
            print("Could not connect to the specified host using specified "
                  "username and password")
            return -1

        atexit.register(connect.Disconnect, service_instance)
        create_basic_vm(service_instance, args.vm_name, args.host_name,
                        args.folder_name, args.datastore_name)

    except vmodl.MethodFault as e:
        print("Caught vmodl fault : {}".format(e.msg))
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
