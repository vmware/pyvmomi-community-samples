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
    disk = None
    for d in storage.ListVStorageObject(datastore):
        disk_info = storage.RetrieveVStorageObject(d, datastore)
        if disk_info.config.name == vdisk:
            disk = disk_info
            break
    if not disk:
        raise RuntimeError("First Class Disk not found.")
    return disk


def retrieve_fcd_snapshot(content, datastore, vdisk, snapshot):
    """
    Retrieves the managed object for the fcd snapshot specified

    Sample Usage:

    retrieve_fcd_snapshot(content, datastore, vdisk, "Snapshot Name")
    """
    # Set vStorageObjectManager
    storage = content.vStorageObjectManager

    # Retrieve Snapshot
    snap = None
    snaps = storage.RetrieveSnapshotInfo(vdisk.config.id, datastore)
    for s in snaps.snapshots:
        if s.description == snapshot:
            snap = s.id
            break
    if not snap:
        raise RuntimeError("Snapshot not found.")
    return snap
