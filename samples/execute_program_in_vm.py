"""
Written by Timo Sugliani
Github: https://github.com/tsugliani/

Code based on upload_file_to_vm snippet by Reubenur Rahman
Github: https://github.com/rreubenur/

This code is released under the terms of the Apache 2
http://www.apache.org/licenses/LICENSE-2.0.html

Example:

python execute_program_in_vm.py
    -s <vcenter_fqdn>
    -u <vcenter_username>
    -p <vcenter_password>
    -v <UUID>
    -r <vm_username>
    -w <vm_password>
    -l "/bin/cat"
    -f "/etc/network/interfaces > /tmp/plop"

    This should work on any debian/ubuntu type of vm, and will basically copy
    the content of the network configuration to /tmp/plop

"""
import time
import re
from tools import cli, service_instance, pchelper
from pyVmomi import vim, vmodl


def main():
    """
    Simple command-line program for executing a process in the VM without the
    network requirement to actually access it.
    """

    parser = cli.Parser()
    parser.add_optional_arguments(
        cli.Argument.VM_NAME, cli.Argument.UUID, cli.Argument.VM_USER, cli.Argument.VM_PASS)
    parser.add_custom_argument('--path_to_program', required=False, action='store',
                               help='Path inside VM to the program. e.g. "/bin/cat"')
    parser.add_custom_argument('--program_arguments', required=False, action='store',
                               help='Program command line options. '
                                    'e.g. "/etc/network/interfaces > /tmp/plop"')
    args = parser.get_args()
   
    si = service_instance.connect(args)
    try:
        content = si.RetrieveContent()

        vm = None
        if args.uuid:
            # if instanceUuid(last argument) is false it will search for VM BIOS UUID instead
            vm = content.searchIndex.FindByUuid(None, args.uuid, True)
        elif args.vm_name:
            vm = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)

        if not vm:
            raise SystemExit("Unable to locate the virtual machine.")

        tools_status = vm.guest.toolsStatus
        if tools_status in ('toolsNotInstalled', 'toolsNotRunning'):
            raise SystemExit(
                "VMwareTools is either not running or not installed. "
                "Rerun the script after verifying that VMwareTools "
                "is running")

        creds = vim.vm.guest.NamePasswordAuthentication(
            username=args.vm_user, password=args.vm_password
        )

        try:
            profile_manager = content.guestOperationsManager.processManager

            if args.program_arguments:
                program_spec = vim.vm.guest.ProcessManager.ProgramSpec(
                    programPath=args.path_to_program,
                    arguments=args.program_arguments)
            else:
                program_spec = vim.vm.guest.ProcessManager.ProgramSpec(
                    programPath=args.path_to_program)

            res = profile_manager.StartProgramInGuest(vm, creds, program_spec)

            if res > 0:
                print("Program submitted, PID is %d" % res)
                pid_exitcode = \
                    profile_manager.ListProcessesInGuest(vm, creds, [res]).pop().exitCode
                # If its not a numeric result code, it says None on submit
                while re.match('[^0-9]+', str(pid_exitcode)):
                    print("Program running, PID is %d" % res)
                    time.sleep(5)
                    pid_exitcode = \
                        profile_manager.ListProcessesInGuest(vm, creds, [res]).pop().exitCode
                    if pid_exitcode == 0:
                        print("Program %d completed with success" % res)
                        break
                    # Look for non-zero code to fail
                    elif re.match('[1-9]+', str(pid_exitcode)):
                        print("ERROR: Program %d completed with Failute" % res)
                        print("  tip: Try running this on guest %r to debug"
                              % vm.summary.guest.ipAddress)
                        print("ERROR: More info on process")
                        print(profile_manager.ListProcessesInGuest(vm, creds, [res]))
                        break

        except IOError as ex:
            print(ex)
    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
