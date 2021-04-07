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

from tools import cli, tasks, service_instance, pbmhelper, pchelper
from pyVmomi import vmodl, vim


def main():
    """
    Simple command-line program for creating a first class disk.
    """

    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.DATASTORE_NAME,cli.Argument.FIRST_CLASS_DISK_NAME)
    parser.add_optional_arguments(cli.Argument.STORAGE_POLICY_NAME)
    parser.add_custom_argument('--capacityInGB', required=True, action='store', type=int,
                                        help='Size in GB of the First Class Disk.')
    parser.add_custom_argument('--keepAfterDeleteVm', action='store_true',
                                        help='Keep after VM deletion. Choice of the '
                                             'deletion behavior of this virtual storage object. '
                                             'If not set, the default value is false.')
    args = parser.get_args()
    serviceInstance = service_instance.connect(args)

    try:
        content = serviceInstance.RetrieveContent()

        # Connect to SPBM Endpoint
        pbmSi = pbmhelper.create_pbm_session(serviceInstance._stub)
        pbmContent = pbmSi.RetrieveContent()

        # Retrieving Storage Policy
        if args.storage_policy_name:
            policy = pbmhelper.retrieve_storage_policy(pbmContent, args.storage_policy_name)
        else:
            policy = None

        # Retrieve Datastore Object
        datastore = pchelper.get_obj(content, [vim.Datastore], args.datastore_name)

        # Setting FCD Specifications
        spec = vim.vslm.CreateSpec()
        spec.name = args.fcd_name
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
        tasks.wait_for_tasks(serviceInstance, [task])
        print("FCD created!")

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
