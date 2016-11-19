#!/usr/bin/env python

"""
vSphere Python SDK program to perform snapshot operations.
"""

import atexit
import argparse
import sys
import time
import ssl

from pyVmomi import vim, vmodl
from pyVim import connect
from pyVim.connect import Disconnect, SmartConnect, GetSi

inputs = {'vcenter_ip': '192.168.1.10',
          'vcenter_password': 'my_password',
          'vcenter_user': 'root',
          'vm_name': 'dummy_vm',
          # operation in 'create/remove/revert/
          # list_all/list_current/remove_all'
          'operation': 'create',
          'snapshot_name': 'snap1',
          'ignore_ssl': True
          }


def get_obj(content, vimtype, name):
    """
     Get the vsphere object associated with a given text name
    """
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def wait_for_task(task, raiseOnError=True, si=None, pc=None):
    if si is None:
        si = GetSi()

    if pc is None:
        sc = si.RetrieveContent()
        pc = sc.propertyCollector

    # First create the object specification as the task object.
    objspec = vmodl.Query.PropertyCollector.ObjectSpec()
    objspec.SetObj(task)

    # Next, create the property specification as the state.
    propspec = vmodl.Query.PropertyCollector.PropertySpec()
    propspec.SetType(vim.Task)
    propspec.SetPathSet(["info.state"])
    propspec.SetAll(True)

    # Create a filter spec with the specified object and property spec.
    filterspec = vmodl.Query.PropertyCollector.FilterSpec()
    filterspec.SetObjectSet([objspec])
    filterspec.SetPropSet([propspec])

    # Create the filter
    filter = pc.CreateFilter(filterspec, True)

    # Loop looking for updates till the state moves to a completed state.
    taskName = task.GetInfo().GetName()
    update = pc.WaitForUpdates(None)
    state = task.GetInfo().GetState()
    while state != vim.TaskInfo.State.success and \
            state != vim.TaskInfo.State.error:
        if (state == 'running') and (taskName.info.name != "Destroy"):
            # check to see if VM needs to ask a question, thow exception
            vm = task.GetInfo().GetEntity()
            if vm is not None and isinstance(vm, vim.VirtualMachine):
                qst = vm.GetRuntime().GetQuestion()
            if qst is not None:
                raise Exception("Task blocked, User Intervention required")

    update = pc.WaitForUpdates(update.GetVersion())
    state = task.GetInfo().GetState()

    filter.Destroy()
    if state == "error" and raiseOnError:
        raise task.GetInfo().GetError()

    return state


def invoke_and_track(func, *args, **kw):
    try:
        task = func(*args, **kw)
        wait_for_task(task)
    except:
        raise


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

    try:
        si = None
        try:
            print("Trying to connect to VCENTER SERVER . . .")

            context = None
            if inputs['ignore_ssl']:
                context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
                context.verify_mode = ssl.CERT_NONE

            si = connect.Connect(inputs['vcenter_ip'], 443,
                                 inputs['vcenter_user'], inputs[
                                     'vcenter_password'],
                                 sslContext=context)
        except IOError, e:
            pass
            atexit.register(Disconnect, si)

        print("Connected to VCENTER SERVER !")

        content = si.RetrieveContent()

        operation = inputs['operation']
        vm_name = inputs['vm_name']

        vm = get_obj(content, [vim.VirtualMachine], vm_name)

        if operation != 'create' and vm.snapshot is None:
            print("Virtual Machine %s doesn't have any snapshots" % vm.name)
            sys.exit()

        if operation == 'create':
            snapshot_name = inputs['snapshot_name']
            description = "Test snapshot"
            dumpMemory = False
            quiesce = False

            print("Creating snapshot %s for virtual machine %s" % (
                                            snapshot_name, vm.name))
            invoke_and_track(vm.CreateSnapshot(
                snapshot_name, description, dumpMemory, quiesce))

        elif operation in ['remove', 'revert']:
            snapshot_name = inputs['snapshot_name']
            snap_obj = get_snapshots_by_name_recursively(
                                vm.snapshot.rootSnapshotList, snapshot_name)
            # if len(snap_obj) is 0; then no snapshots with specified name
            if len(snap_obj) == 1:
                snap_obj = snap_obj[0].snapshot
                if operation == 'remove':
                    print("Removing snapshot %s" % snapshot_name)
                    invoke_and_track(snap_obj.RemoveSnapshot_Task(True))
                else:
                    print("Reverting to snapshot %s" % snapshot_name)
                    invoke_and_track(snap_obj.RevertToSnapshot_Task())

        elif operation == 'list_all':
            print("Display list of snapshots on virtual machine %s" % vm.name)
            snapshot_paths = list_snapshots_recursively(
                                vm.snapshot.rootSnapshotList)
            for snapshot in snapshot_paths:
                print(snapshot)

        elif operation == 'list_current':
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

        elif operation == 'remove_all':
            print("Removing all snapshots for virtual machine %s" % vm.name)
            invoke_and_track(vm.RemoveAllSnapshots())

        else:
            print("Specify operation in "
                  "create/remove/revert/list_all/list_current/remove_all")

    except vmodl.MethodFault, e:
        print("Caught vmodl fault: %s" % e.msg)
        return 1
    except Exception, e:
        if str(e).startswith("'vim.Task'"):
            return 1
        print("Caught exception: %s" % str(e))
        return 1

# Start program
if __name__ == "__main__":
    main()
