from pyVmomi import vim
from tools import cli, service_instance, pchelper, tasks
from pyVim.task import WaitForTasks


def main():
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.VM_NAME)
    parser.add_optional_arguments(cli.Argument.POWER_ON)
    # custom argument to get CPU count
    parser.add_custom_argument('--cpu', required=False, action='store', default=None,
                               help='Version/release number of the Virtual machine CPUs')
    args = parser.get_args()
    si = service_instance.connect(args)

    content = si.RetrieveContent()
    # getting vm details
    vm = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)
    OLDCPU = vm.config.hardware.numCPU
    if not vm:
        print("Could not find VM %s" % args.vm_name)
    else:
        print("Upgrading VM CPUs %s" % args.vm_name)

        if args.cpu is not None:
            print("Upgraded CPU will be %s" % args.cpu)
            # updating CPU
            CPU = int(vm.config.hardware.numCPU) + int(args.cpu)
        else:
            CPU = vm.config.hardware.numCPU

        if OLDCPU < CPU:
            # Powering off VM for CPU change
            if format(vm.runtime.powerState) == "poweredOn":
                print("Attempting to power off {0}".format(vm.name))
                TASK = vm.PowerOffVM_Task()
                tasks.wait_for_tasks(si, [TASK])
                print("{0}".format(TASK.info.state))

            spec = vim.vm.ConfigSpec()
            spec.numCPUs = CPU
            WaitForTasks([vm.ReconfigVM_Task(spec=spec)], si=si)
            print(vm.config.hardware.numCPU)

            if args.power_on:
                task = vm.PowerOnVM_Task()
                tasks.wait_for_tasks(si, [task])
                print("{0}".format(task.info.state))
        else:
            print("provide valid argument")


# Start the script
if __name__ == '__main__':
    main()