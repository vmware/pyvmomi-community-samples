#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Written by Chris Arceneaux
# GitHub: https://github.com/carceneaux
# Email: carceneaux@thinksis.com
# Website: http://arsano.ninja
#
# Note: Example code For testing purposes only
#
# This code has been released under the terms of the Apache-2.0 license
# http://opensource.org/licenses/Apache-2.0

"""
Python program for deleting a first class disk (fcd)
"""

import atexit

from tools import cli, tasks
from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim


def get_args():
    """
    Adds additional args for deleting a fcd

    -d datastore
    -v vdisk
    -y yes
    """
    parser = cli.build_arg_parser()

    parser.add_argument('-d', '--datastore',
                        required=True,
                        action='store',
                        help='Datastore name where disk is located')

    parser.add_argument('-v', '--vdisk',
                        required=True,
                        action='store',
                        help='First Class Disk name to be deleted')

    parser.add_argument('-y', '--yes',
                        action='store_true',
                        help='Confirm disk deletion.')

    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)


def get_obj(content, vimtype, name):
    """
    Retrieves the managed object for the name and type specified
    """
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def retrieve_fcd(content, datastore, vdisk):
    """
    Retrieves the managed object for the first class disk specified
    """
    # Set vStorageObjectManager
    storage = content.vStorageObjectManager

    # Retrieve First Class Disks
    disk = None
    for d in storage.ListVStorageObject(datastore):
        disk_info = storage.RetrieveVStorageObject(d, datastore)
        if disk_info.config.name == vdisk:
            disk = disk_info
            break
    if not disk:
        raise RuntimeError("First Class Disk not found.")
    return disk


def main():
    """
    Simple command-line program for deleting a snapshot of a first class disk.
    """

    args = get_args()

    try:
        if args.disable_ssl_verification:
            service_instance = connect.SmartConnectNoSSL(host=args.host,
                                                         user=args.user,
                                                         pwd=args.password,
                                                         port=int(args.port))
        else:
            service_instance = connect.SmartConnect(host=args.host,
                                                    user=args.user,
                                                    pwd=args.password,
                                                    port=int(args.port))

        atexit.register(connect.Disconnect, service_instance)

        content = service_instance.RetrieveContent()

        # Retrieve Datastore Object
        datastore = get_obj(content, [vim.Datastore], args.datastore)

        # Retrieve FCD Object
        vdisk = retrieve_fcd(content, datastore, args.vdisk)

        # Confirming FCD deletion
        if not args.yes:
            response = cli.prompt_y_n_question("Are you sure you want to "
                                               "delete vdisk '" + args.vdisk +
                                               "'?",
                                               default='no')
            if not response:
                print("Exiting script. User chose not to delete HDD.")
                exit()

        # Delete FCD
        storage = content.vStorageObjectManager
        task = storage.DeleteVStorageObject_Task(vdisk.config.id, datastore)
        tasks.wait_for_tasks(service_instance, [task])

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
