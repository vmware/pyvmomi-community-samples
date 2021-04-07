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

from tools import cli, tasks, disk, pchelper, service_instance
from pyVmomi import vmodl
from pyVmomi import vim


def main():
    """
    Simple command-line program for creating a snapshot of a first class disk.
    """

    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.DATASTORE_NAME, cli.Argument.FIRST_CLASS_DISK_NAME, cli.Argument.SNAPSHOT_NAME)
    args = parser.get_args()
    serviceInstance = service_instance.connect(args)

    try:
        content = serviceInstance.RetrieveContent()

        # Retrieve Datastore Object
        datastore = pchelper.get_obj(content, [vim.Datastore], args.datastore_name)

        # Retrieve FCD Object
        vdisk = disk.retrieve_fcd(content, datastore, args.fcd_name)

        # Create FCD Snapshot
        storage = content.vStorageObjectManager
        task = storage.VStorageObjectCreateSnapshot_Task(
            vdisk.config.id, datastore, args.snapshot_name)
        tasks.wait_for_tasks(serviceInstance, [task])

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
