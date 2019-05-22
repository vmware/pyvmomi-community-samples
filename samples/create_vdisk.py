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
Python program for creating a first class disk (fcd)
"""

import atexit

from tools import cli, tasks, disk, pbmhelper
from pyVim import connect
from pyVmomi import vmodl, vim


def get_args():
    """
    Adds additional args for creating a fcd

    -d datastore
    -n name
    -c capacityInGB
    -e policy
    -k keepAfterDeleteVm
    """
    parser = cli.build_arg_parser()

    parser.add_argument('-d', '--datastore',
                        required=True,
                        action='store',
                        help='Datastore name where disk is located')

    parser.add_argument('-n', '--name',
                        required=True,
                        action='store',
                        help='First Class Disk name to be created')

    parser.add_argument('-c', '--capacityInGB',
                        required=True,
                        action='store',
                        help='Size in GB of the First Class Disk.',
                        type=int)

    # because -s is reserved for 'service' and -p is reserved for 'password'
    parser.add_argument('-e', '--policy',
                        action='store',
                        help='Storage Policy name. If unset, the default '
                        'policy of the datastore specified will apply.')

    parser.add_argument('-k', '--keepAfterDeleteVm',
                        action='store_true',
                        help='Keep after VM deletion. Choice of the '
                        'deletion behavior of this virtual storage object. '
                        'If not set, the default value is false.')

    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)


def main():
    """
    Simple command-line program for creating a first class disk.
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
            policy = pbmhelper.retrieve_storage_policy(pbmContent, args.policy)
        else:
            policy = None

        # Retrieve Datastore Object
        datastore = disk.get_obj(content, [vim.Datastore], args.datastore)

        # Setting FCD Specifications
        spec = vim.vslm.CreateSpec()
        spec.name = args.name
        spec.capacityInMB = args.capacityInGB * 1024
        if args.keepAfterDeleteVm:
            spec.keepAfterDeleteVm = True
        spec.backingSpec = vim.vslm.CreateSpec.DiskFileBackingSpec()
        spec.backingSpec.provisioningType = "thin"
        spec.backingSpec.datastore = datastore
        if policy:
            spec.profile = [vim.vm.DefinedProfileSpec(
                profileId=policy.profileId.uniqueId)]

        # Create FCD
        storage = content.vStorageObjectManager
        task = storage.CreateDisk_Task(spec)
        tasks.wait_for_tasks(service_instance, [task])

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
