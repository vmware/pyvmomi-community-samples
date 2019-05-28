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

from tools import cli, tasks, disk, pbmhelper
from pyVim import connect
from pyVmomi import vmodl, vim, pbm, VmomiSupport


def get_args():
    """
    Adds additional args for creating a fcd from a snapshot

    -d source_datastore
    -v source_vdisk
    -n snapshot
    -D dest_datastore
    -V dest_vdisk
    """
    parser = cli.build_arg_parser()

    parser.add_argument('-d', '--source_datastore',
                        required=True,
                        action='store',
                        help='Datastore name where source disk is located')

    parser.add_argument('-v', '--source_vdisk',
                        required=True,
                        action='store',
                        help='First Class Disk name with specified snapshot')

    # because -s is reserved for 'service', we use -n for snapshot name
    parser.add_argument('-n', '--snapshot',
                        required=True,
                        action='store',
                        help='Snapshot name to be cloned')

    parser.add_argument('-D', '--dest_datastore',
                        required=True,
                        action='store',
                        help='Datastore name where new disk is located')

    parser.add_argument('-V', '--dest_vdisk',
                        required=True,
                        action='store',
                        help='First Class Disk name to be created')

    # because -s is reserved for 'service' and -p is reserved for 'password'
    parser.add_argument('-e', '--policy',
                        action='store',
                        help='Storage Policy name for new disk. If unset, '
                        'the default policy of the datastore specified '
                        'will apply.')

    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)


def main():
    """
    Simple command-line program for creating a new vdisk from a snapshot
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

        # Connect to SPBM Endpoint
        pbmSi = pbmhelper.create_pbm_session(service_instance._stub)
        pbmContent = pbmSi.RetrieveContent()

        # Retrieving Storage Policy
        if args.policy:
            p = pbmhelper.retrieve_storage_policy(pbmContent, args.policy)
            policy = [vim.vm.DefinedProfileSpec(
                profileId=p.profileId.uniqueId)]
        else:
            policy = None

        # Retrieve Source Datastore Object
        source_datastore = disk.get_obj(
            content, [vim.Datastore], args.source_datastore)

        # Retrieve Source FCD Object
        source_vdisk = disk.retrieve_fcd(
            content, source_datastore, args.source_vdisk)

        # Retrieve Snapshot Object
        snapshot = disk.retrieve_fcd_snapshot(
            content, source_datastore, source_vdisk, args.snapshot)

        # Retrieve Destination Datastore Object
        dest_datastore = disk.get_obj(
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
        tasks.wait_for_tasks(service_instance, [task])

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
