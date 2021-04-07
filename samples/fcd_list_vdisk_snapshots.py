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

from tools import cli, disk, pchelper, service_instance
from pyVmomi import vmodl, vim


def list_fcd_snapshots(content, vdisk):
    """
    List all the snapshots for the specified first class disk
    """
    # Set vStorageObjectManager
    storage = content.vStorageObjectManager

    # Retrieve all Snapshots
    snapshots = storage.RetrieveSnapshotInfo(
        vdisk.config.id, vdisk.config.backing.datastore).snapshots
    if len(snapshots) > 0:
        # Print snapshot information
        print("")
        for snapshot in snapshots:
            print("Name: %s " % snapshot.description)
            print("ID: %s " % snapshot.id.id)
            print("Create Time: %s " % snapshot.createTime)
            print("")
    else:
        print("No snapshots found for this vdisk.")


def main():
    """
    Simple command-line program for listing all snapshots of a fcd
    """

    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.DATASTORE_NAME, cli.Argument.FIRST_CLASS_DISK_NAME)
    args = parser.get_args()
    si = service_instance.connect(args)

    try:
        content = si.RetrieveContent()

        # Retrieve Datastore Object
        datastore = pchelper.get_obj(content, [vim.Datastore], args.datastore_name)

        # Retrieve FCD Object
        vdisk = disk.retrieve_fcd(content, datastore, args.fcd_name)

        # Retrieve all Snapshots
        list_fcd_snapshots(content, vdisk)

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
