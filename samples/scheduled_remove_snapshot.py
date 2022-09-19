#!/usr/bin/env python

from datetime import datetime, timedelta
from tools import cli, service_instance
from pyVmomi import vim
from pyVim import connect


def get_snapshots_by_name_recursively(snapshots, snapname):
    snap_obj = []
    for snapshot in snapshots:
        if snapshot.name == snapname:
            snap_obj.append(snapshot)
        else:
            snap_obj = snap_obj + get_snapshots_by_name_recursively(
                snapshot.childSnapshotList, snapname)
    return snap_obj


def main():
    print("Trying to connect to VCENTER SERVER . . .")
    parser = cli.Parser()
    parser.add_required_arguments(
        cli.Argument.MINUTES, cli.Argument.VM_NAME, cli.Argument.SNAPSHOT_NAME)
    parser.add_optional_arguments(cli.Argument.POWER_ON)
    args = parser.get_args()
    try:
        date_time = datetime.now() + timedelta(minutes=int(args.minutes))
    except ValueError:
        print('Unrecognized date format')
        return -1

    si = service_instance.connect(args)

    print("Connected to VCENTER SERVER !")

    view = si.content.viewManager.CreateContainerView(si.content.rootFolder,
                                                      [vim.VirtualMachine],
                                                      True)
    vms = [vm for vm in view.view if vm.name == args.vm_name]

    if not vms:
        print('VM not found')
        connect.Disconnect(si)
        return -1
    vm = vms[0]

    snap_obj = get_snapshots_by_name_recursively(
        vm.snapshot.rootSnapshotList, args.snapshot_name)
    print("type")
    print(type(snap_obj[0].snapshot))
    print(snap_obj)
    if len(snap_obj) == 1:
        snap_obj = snap_obj[0].snapshot
        spec = vim.scheduler.ScheduledTaskSpec()
        spec.name = args.snapshot_name + args.vm_name + "remove"
        spec.action = vim.action.MethodAction()
        spec.scheduler = vim.scheduler.OnceTaskScheduler()
        spec.scheduler.runAt = date_time
        spec.action.name = vim.vm.Snapshot.RemoveSnapshot_Task

    else:
        print("No snapshots found with name: %s on VM: %s" % (
            args.snapshot_name, vm.name))

    spec.action.argument = [vim.MethodActionArgument()] * 1
    spec.action.argument[0] = vim.MethodActionArgument()
    spec.action.argument[0].value = False
    spec.enabled = True
    if si.content.scheduledTaskManager.CreateObjectScheduledTask(snap_obj, spec) is not None:
        print('Scheduled Task Successfully')
    return 0


if __name__ == "__main__":
    main()
