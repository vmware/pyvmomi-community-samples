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
Python program for deleting a snapshot of a first class disk (fcd)
"""

import atexit

from tools import cli, tasks, disk, pchelper, service_instance
from pyVmomi import vmodl
from pyVmomi import vim


def main():
    """
    Simple command-line program for deleting a snapshot of a first class disk.
    """

    parser = cli.Parser()
    parser.add_required_arguments(
    cli.Argument.DATASTORE_NAME, cli.Argument.FIRST_CLASS_DISK_NAME, cli.Argument.SNAPSHOT_NAME)
    parser.add_custom_argument('--yes', action='store_true', help='Confirm disk deletion.')
    args = parser.get_args()
    serviceInstance = service_instance.connect(args)

    try:
        content = serviceInstance.RetrieveContent()

        # Retrieve Datastore Object
        datastore = pchelper.get_obj(content, [vim.Datastore], args.datastore_name)

        # Retrieve FCD Object
        vdisk = disk.retrieve_fcd(content, datastore, args.fcd_name)

        # Retrieve Snapshot Object
        snapshot = disk.retrieve_fcd_snapshot(
            content, datastore, vdisk, args.snapshot_name)

        # Confirming Snapshot deletion
        if not args.yes:
            response = cli.prompt_y_n_question("Are you sure you want to "
                                               "delete snapshot '" +
                                               args.snapshot_name + "'?",
                                               default='no')
            if not response:
                print("Exiting script. User chose not to delete snapshot.")
                exit()

        # Delete FCD Snapshot
        storage = content.vStorageObjectManager
        task = storage.DeleteSnapshot_Task(
            vdisk.config.id, datastore, snapshot)
        tasks.wait_for_tasks(serviceInstance, [task])

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
