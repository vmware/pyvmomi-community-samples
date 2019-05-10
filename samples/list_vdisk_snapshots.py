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
Python program for listing all snapshots of a first class disk (fcd)
"""

import atexit

from tools import cli, tasks
from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim


def get_args():
    """
    Adds additional args for listing all snapshots of a fcd

    -d datastore
    -v vdisk
    """
    parser = cli.build_arg_parser()

    parser.add_argument('-d', '--datastore',
                        required=True,
                        action='store',
                        help='Datastore name where disk is located')

    parser.add_argument('-v', '--vdisk',
                        required=True,
                        action='store',
                        help='First Class Disk name to delete snapshot for')

    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)


def get_obj(content, vimtype, name):
    """
    Retrieves the vmware object for the name and type specified
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
    Retrieves the vmware object for the first class disk specified
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


def retrieve_snapshots(content, vdisk):
    """
    Retrieves the vmware object for the snapshot specified
    """
    # Set vStorageObjectManager
    storage = content.vStorageObjectManager

    # Retrieve all Snapshots
    snapshots = storage.RetrieveSnapshotInfo(
        vdisk.config.id, vdisk.config.backing.datastore).snapshots
    if len(snapshots) > 0:
        # Print snapshot information
        print("")
        for s in snapshots:
            print("Name: %s " % s.description)
            print("ID: %s " % s.id.id)
            print("Create Time: %s " % s.createTime)
            print("")
    else:
        print("No snapshots found for this vdisk.")


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

        # Retrieve all Snapshots
        retrieve_snapshots(content, vdisk)

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
