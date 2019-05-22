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
Python program for creating a snapshot of a first class disk (fcd)
"""

import atexit

from tools import cli, tasks, disk
from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim


def get_args():
    """
    Adds additional args for creating a snapshot of a fcd

    -d datastore
    -v vdisk
    -n snapshot
    """
    parser = cli.build_arg_parser()

    parser.add_argument('-d', '--datastore',
                        required=True,
                        action='store',
                        help='Datastore name where disk is located')

    parser.add_argument('-v', '--vdisk',
                        required=True,
                        action='store',
                        help='First Class Disk name to create snapshot for')

    # because -s is reserved for 'service', we use -n for snapshot name
    parser.add_argument('-n', '--snapshot',
                        required=True,
                        action='store',
                        help='New snapshot name')

    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)


def main():
    """
    Simple command-line program for creating a snapshot of a first class disk.
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
        datastore = disk.get_obj(content, [vim.Datastore], args.datastore)

        # Retrieve FCD Object
        vdisk = disk.retrieve_fcd(content, datastore, args.vdisk)

        # Create FCD Snapshot
        storage = content.vStorageObjectManager
        task = storage.VStorageObjectCreateSnapshot_Task(
            vdisk.config.id, datastore, args.snapshot)
        tasks.wait_for_tasks(service_instance, [task])

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
