#!/usr/bin/env python

from datetime import datetime, timedelta
from tools import cli, service_instance
from pyVmomi import vim
from pyVim import connect


def main():
    print("Trying to connect to VCENTER SERVER . . .")
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.MINUTES, cli.Argument.VM_NAME)
    parser.add_optional_arguments(cli.Argument.POWER_ON)
    parser.add_custom_argument('--task', required=False, action='store', default=None,
                               help='Task name for removal of all snapshots')
    args = parser.get_args()
    try:
        date_time = datetime.now() + timedelta(minutes=int(args.minutes))
        print(date_time)
        # dt = datetime.strptime(args.date, '%d/%m/%Y %H:%M')
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

    spec = vim.scheduler.ScheduledTaskSpec()
    spec.name = args.task + args.vm_name
    spec.scheduler = vim.scheduler.OnceTaskScheduler()
    spec.scheduler.runAt = date_time
    spec.action = vim.action.MethodAction()
    spec.action.name = vim.VirtualMachine.RemoveAllSnapshots_Task
    print(spec.action.argument)
    spec.enabled = True
    if si.content.scheduledTaskManager.CreateScheduledTask(vm, spec) is not None:
        print('Scheduled Task Successfully')
    return 0


if __name__ == "__main__":
    main()
