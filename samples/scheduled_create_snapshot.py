#!/usr/bin/env python

from datetime import datetime, timedelta
from tools import cli, service_instance
from pyVmomi import vim
from pyVim import connect


def main():
    print("Trying to connect to VCENTER SERVER . . .")
    parser = cli.Parser()
    parser.add_required_arguments(
        cli.Argument.MINUTES, cli.Argument.VM_NAME, cli.Argument.SNAPSHOT_NAME)
    parser.add_optional_arguments(cli.Argument.POWER_ON)
    parser.add_custom_argument('--description', required=False, action='store', default=None,
                               help='Description of snapshot')
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

    print("Executing Scheduling process !")

    spec = vim.scheduler.ScheduledTaskSpec()
    spec.name = args.snapshot_name + args.vm_name
    spec.description = args.description
    spec.scheduler = vim.scheduler.OnceTaskScheduler()
    spec.scheduler.runAt = date_time
    spec.action = vim.action.MethodAction()
    spec.action.name = vim.VirtualMachine.CreateSnapshot_Task
    spec.action.argument = [vim.MethodActionArgument()] * 4
    spec.action.argument[0] = vim.MethodActionArgument()
    spec.action.argument[0].value = args.snapshot_name
    spec.action.argument[1] = vim.MethodActionArgument()
    spec.action.argument[1].value = args.description
    spec.action.argument[2] = vim.MethodActionArgument()
    spec.action.argument[2].value = True
    spec.action.argument[3] = vim.MethodActionArgument()
    spec.action.argument[3].value = False
    print(spec.action.argument)
    spec.enabled = True
    task = si.content.scheduledTaskManager.CreateScheduledTask(vm, spec)
    if task is not None:
        print('Scheduled Task Successfully')

    return 0


if __name__ == "__main__":
    main()
