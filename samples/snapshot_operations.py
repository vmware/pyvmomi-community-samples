#!/usr/bin/env python

# Copyright 2016 Abdul Anshad <abdulanshad33@gmail.com>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""
Written by Abdul Anshad
Github: https://github.com/Abdul-Anshad-A
Email: abdulanshad33@gmail.com

Credits:
Thanks to "reuben.13@gmail.com" for the initial code.

Note: Example code For testing purposes only
vSphere Python SDK program to perform snapshot operations.
"""

import sys
from tools import cli, pchelper, service_instance
from pyVmomi import vim, vmodl
from pyVim.task import WaitForTask


def list_snapshots_recursively(snapshots):
    snapshot_data = []
    snap_text = ""
    for snapshot in snapshots:
        snap_text = "Name: %s; Description: %s; CreateTime: %s; State: %s" % (
                                        snapshot.name, snapshot.description,
                                        snapshot.createTime, snapshot.state)
        snapshot_data.append(snap_text)
        snapshot_data = snapshot_data + list_snapshots_recursively(
                                        snapshot.childSnapshotList)
    return snapshot_data


def get_snapshots_by_name_recursively(snapshots, snapname):
    snap_obj = []
    for snapshot in snapshots:
        if snapshot.name == snapname:
            snap_obj.append(snapshot)
        else:
            snap_obj = snap_obj + get_snapshots_by_name_recursively(
                                    snapshot.childSnapshotList, snapname)
    return snap_obj


def get_current_snap_obj(snapshots, snapob):
    snap_obj = []
    for snapshot in snapshots:
        if snapshot.snapshot == snapob:
            snap_obj.append(snapshot)
        snap_obj = snap_obj + get_current_snap_obj(
                                snapshot.childSnapshotList, snapob)
    return snap_obj


def main():

    print("Trying to connect to VCENTER SERVER . . .")
    parser = cli.Parser()
    parser.add_optional_arguments(cli.Argument.VM_NAME, cli.Argument.SNAPSHOT_OPERATION, cli.Argument.SNAPSHOT_NAME)
    args = parser.get_args()
    serviceInstance = service_instance.connect(args)

    print("Connected to VCENTER SERVER !")

    content = serviceInstance.RetrieveContent()

    vm = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)

    if args.snapshot_operation != 'create' and vm.snapshot is None:
        print("Virtual Machine %s doesn't have any snapshots" % vm.name)
        sys.exit()

    if args.snapshot_operation == 'create':
        snapshot_name = args.snapshot_name
        description = "Test snapshot"
        dumpMemory = False
        quiesce = False

        print("Creating snapshot %s for virtual machine %s" % (
                                        snapshot_name, vm.name))
        WaitForTask(vm.CreateSnapshot(
            snapshot_name, description, dumpMemory, quiesce))

    elif args.snapshot_operation in ['remove', 'revert']:
        snapshot_name = args.snapshot_name
        snap_obj = get_snapshots_by_name_recursively(
                            vm.snapshot.rootSnapshotList, snapshot_name)
        # if len(snap_obj) is 0; then no snapshots with specified name
        if len(snap_obj) == 1:
            snap_obj = snap_obj[0].snapshot
            if args.snapshot_operation == 'remove':
                print("Removing snapshot %s" % snapshot_name)
                WaitForTask(snap_obj.RemoveSnapshot_Task(True))
            else:
                print("Reverting to snapshot %s" % snapshot_name)
                WaitForTask(snap_obj.RevertToSnapshot_Task())
        else:
            print("No snapshots found with name: %s on VM: %s" % (
                                                snapshot_name, vm.name))

    elif args.snapshot_operation == 'list_all':
        print("Display list of snapshots on virtual machine %s" % vm.name)
        snapshot_paths = list_snapshots_recursively(
                            vm.snapshot.rootSnapshotList)
        for snapshot in snapshot_paths:
            print(snapshot)

    elif args.snapshot_operation == 'list_current':
        current_snapref = vm.snapshot.currentSnapshot
        current_snap_obj = get_current_snap_obj(
                            vm.snapshot.rootSnapshotList, current_snapref)
        current_snapshot = "Name: %s; Description: %s; " \
                           "CreateTime: %s; State: %s" % (
                                current_snap_obj[0].name,
                                current_snap_obj[0].description,
                                current_snap_obj[0].createTime,
                                current_snap_obj[0].state)
        print("Virtual machine %s current snapshot is:" % vm.name)
        print(current_snapshot)

    elif args.snapshot_operation == 'remove_all':
        print("Removing all snapshots for virtual machine %s" % vm.name)
        WaitForTask(vm.RemoveAllSnapshots())

    else:
        print("Specify operation in "
              "create/remove/revert/list_all/list_current/remove_all")

# Start program
if __name__ == "__main__":
    main()
