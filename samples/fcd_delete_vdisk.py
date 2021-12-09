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

import sys
from tools import cli, tasks, disk, pchelper, service_instance
from pyVmomi import vmodl, vim


def main():
    """
    Simple command-line program for deleting a snapshot of a first class disk.
    """

    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.DATASTORE_NAME, cli.Argument.FIRST_CLASS_DISK_NAME)
    parser.add_custom_argument('--yes', action='store_true', help='Confirm disk deletion.')
    args = parser.get_args()
    si = service_instance.connect(args)

    try:
        content = si.RetrieveContent()

        # Retrieve Datastore Object
        datastore = pchelper.get_obj(content, [vim.Datastore], args.datastore_name)

        # Retrieve FCD Object
        vdisk = disk.retrieve_fcd(content, datastore, args.fcd_name)

        # Confirming FCD deletion
        if not args.yes:
            response = cli.prompt_y_n_question("Are you sure you want to "
                                               "delete vdisk '" + args.fcd_name +
                                               "'?",
                                               default='no')
            if not response:
                print("Exiting script. User chose not to delete HDD.")
                sys.exit()

        # Delete FCD
        storage = content.vStorageObjectManager
        task = storage.DeleteVStorageObject_Task(vdisk.config.id, datastore)
        tasks.wait_for_tasks(si, [task])
        print("FCD deleted!")

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
