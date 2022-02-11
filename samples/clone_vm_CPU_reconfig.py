from pyVmomi import vim
from pyVim.task import WaitForTasks, WaitForTask
from tools import cli, pchelper, service_instance, tasks

def clone_vm_CPU_reconfig(si, vm_name, new_vmname, datacenter_name, host_ip, power_on, datastore_name=None, cpu=None, memory=None):
    content = si.RetrieveContent()
    VM = pchelper.get_obj(content, [vim.VirtualMachine], vm_name)
    datacenter = pchelper.get_obj(content, [vim.Datacenter], datacenter_name)
    destination_host = pchelper.get_obj(content, [vim.HostSystem], host_ip)
    destfolder = datacenter.vmFolder
    host_dest_ip = destination_host.parent.host[0]
    source_pool = destination_host.parent.resourcePool
    for i in range(len(destination_host.parent.host)):
        if destination_host.parent.host[i].name == host_ip:
            host_dest_ip = destination_host.parent.host[i]

    if datastore_name:
        datastore = pchelper.search_for_obj(content, [vim.Datastore], datastore_name)
    else:
        datastore = pchelper.get_obj(
            content, [vim.Datastore], VM.datastore[0].info.name)

    if cpu is None:
        cpu = 2
    if memory is None:
        memory = 4

    relospec = vim.vm.RelocateSpec()
    relospec.datastore = datastore
    relospec.pool = source_pool
    relospec.host = host_dest_ip

    clonespec = vim.vm.CloneSpec()
    clonespec.location = relospec

    print("Running Task")
    task = VM.Clone(folder=destfolder, name=new_vmname, spec=clonespec)
    WaitForTask(task)
    print("vm cloned")

    vm = pchelper.get_obj(content, [vim.VirtualMachine], new_vmname)
    config = create_config_spec(cpus=cpu, memory=memory)
    WaitForTasks([vm.ReconfigVM_Task(spec=config)], si=si)
    print(vm.config.hardware.numCPU)

    if power_on:
        TASK = vm.PowerOnVM_Task()
        tasks.wait_for_tasks(si, [TASK])
        print("{0}".format(TASK.info.state))

    print("VM All tasks completed.")


def create_config_spec(memory, cpus):
    config = vim.vm.ConfigSpec()
    config.memoryMB = int(memory)
    config.numCPUs = int(cpus)
    return config

def main():
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.VM_NAME, cli.Argument.DATACENTER_NAME,
                                  cli.Argument.DATASTORE_NAME, cli.Argument.ESX_IP,)
    parser.add_optional_arguments(cli.Argument.POWER_ON)

    parser.add_custom_argument('--cpu', required=False, action='store', default=None,
                               help='Version/release CPUs of the Virtual machine CPUs')

    parser.add_custom_argument('--memory', required=False, action='store', default=None,
                               help='Version/release memory of the Virtual machine memories')

    parser.add_custom_argument('--clone_name', required=False, action='store', default=None,
                               help='Version/release name of the Virtual machine clone name')
    args = parser.get_args()
    si = service_instance.connect(args)
    clone_vm_CPU_reconfig(si, args.vm_name, args.clone_name, args.datacenter_name, args.esx_ip, args.power_on, args.datastore_name, args.cpu, args.memory)


# start this thing
if __name__ == "__main__":
    main()