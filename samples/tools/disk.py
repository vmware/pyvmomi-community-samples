# Written by Chris Arceneaux
# GitHub: https://github.com/carceneaux
# Email: carceneaux@thinksis.com
# Website: http://arsano.ninja
#
# This code has been released under the terms of the Apache-2.0 license
# http://opensource.org/licenses/Apache-2.0

"""
This module implements simple helper functions for working with:

- Virtual Machine Disks
- First Class Disks
"""


def retrieve_fcd(content, datastore, vdisk):
    """
    Retrieves the managed object for the first class disk specified

    Sample Usage:

    retrieve_fcd(content, datastore, "First Class Disk Name")
    """
    # Set vStorageObjectManager
    storage = content.vStorageObjectManager

    # Retrieve First Class Disks
    fcd = None
    for disk in storage.ListVStorageObject(datastore):
        disk_info = storage.RetrieveVStorageObject(disk, datastore)
        if disk_info.config.name == vdisk:
            fcd = disk_info
            break
    if not fcd:
        raise RuntimeError("First Class Disk not found.")
    return fcd


def retrieve_fcd_snapshot(content, datastore, vdisk, snapshot_name):
    """
    Retrieves the managed object for the fcd snapshot specified

    Sample Usage:

    retrieve_fcd_snapshot(content, datastore, vdisk, "Snapshot Name")
    """
    # Set vStorageObjectManager
    storage = content.vStorageObjectManager

    # Retrieve Snapshot
    fcd_snapshot = None
    snaps = storage.RetrieveSnapshotInfo(vdisk.config.id, datastore)
    for snapshot in snaps.snapshots:
        if snapshot.description == snapshot_name:
            fcd_snapshot = snapshot.id
            break
    if not fcd_snapshot:
        raise RuntimeError("Snapshot not found.")
    return fcd_snapshot
