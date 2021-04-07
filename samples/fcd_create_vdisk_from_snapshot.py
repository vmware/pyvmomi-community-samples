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
Python program for creating a first class disk (fcd) from a snapshot
"""

import atexit

from tools import cli, tasks, disk, pbmhelper, pchelper, service_instance
from pyVmomi import vmodl, vim, pbm


def main():
    """
    Simple command-line program for creating a new vdisk from a snapshot
    """

    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.SNAPSHOT_NAME)
    parser.add_optional_arguments(cli.Argument.STORAGE_POLICY_NAME)
    parser.add_custom_argument('--source_datastore', required=True, action='store',
                                        help='Datastore name where source disk is located')
    parser.add_custom_argument('--source_vdisk', required=True, action='store',
                                        help='First Class Disk name with specified snapshot')
    parser.add_custom_argument('--dest_datastore', required=True, action='store',
                                        help='Datastore name where new disk is located')
    parser.add_custom_argument('--dest_vdisk', required=True, action='store',
                                        help='First Class Disk name to be created')
    args = parser.get_args()
    serviceInstance = service_instance.connect(args)

    try:
        content = serviceInstance.RetrieveContent()

        # Connect to SPBM Endpoint
        pbmSi = pbmhelper.create_pbm_session(serviceInstance._stub)
        pbmContent = pbmSi.RetrieveContent()

        # Retrieving Storage Policy
        if args.storage_policy_name:
            p = pbmhelper.retrieve_storage_policy(pbmContent, args.storage_policy_name)
            policy = [vim.vm.DefinedProfileSpec(
                profileId=p.profileId.uniqueId)]
        else:
            policy = None

        # Retrieve Source Datastore Object
        source_datastore = pchelper.get_obj(
            content, [vim.Datastore], args.source_datastore)

        # Retrieve Source FCD Object
        source_vdisk = disk.retrieve_fcd(
            content, source_datastore, args.source_vdisk)

        # Retrieve Snapshot Object
        snapshot = disk.retrieve_fcd_snapshot(
            content, source_datastore, source_vdisk, args.snapshot_name)

        # Retrieve Destination Datastore Object
        dest_datastore = pchelper.get_obj(
            content, [vim.Datastore], args.dest_datastore)

        # Create FCD from Snapshot
        storage = content.vStorageObjectManager
        if policy:
            task = storage.CreateDiskFromSnapshot_Task(
                source_vdisk.config.id,
                dest_datastore,
                snapshot,
                args.dest_vdisk,
                policy)
        else:
            task = storage.CreateDiskFromSnapshot_Task(
                source_vdisk.config.id,
                dest_datastore,
                snapshot,
                args.dest_vdisk)
        tasks.wait_for_tasks(serviceInstance, [task])

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
