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
    -v <vm_uuid>
    -r <vm_username>
    -w <vm_password>
    -l "/bin/cat"
    -f "/etc/network/interfaces > /tmp/plop"

    This should work on any debian/ubuntu type of vm, and will basically copy
    the content of the network configuration to /tmp/plop

"""
from __future__ import with_statement
import atexit
from tools import cli
from pyVim import connect
from pyVmomi import vim, vmodl


def get_args():
    """Get command line args from the user.
    """

    parser = cli.build_arg_parser()

    parser.add_argument('-v', '--vm_uuid',
                        required=False,
                        action='store',
                        help='Virtual machine uuid')

    parser.add_argument('-r', '--vm_user',
                        required=False,
                        action='store',
                        help='virtual machine user name')

    parser.add_argument('-w', '--vm_pwd',
                        required=False,
                        action='store',
                        help='virtual machine password')

    parser.add_argument('-l', '--path_to_program',
                        required=False,
                        action='store',
                        help='Path inside VM to the program')

    parser.add_argument('-f', '--program_arguments',
                        required=False,
                        action='store',
                        help='Program command line options')

    args = parser.parse_args()

    cli.prompt_for_password(args)
    return args


def main():
    """
    Simple command-line program for executing a process in the VM without the
    network requirement to actually access it.
    """

    args = get_args()
    try:
        service_instance = connect.SmartConnect(host=args.host,
                                                user=args.user,
                                                pwd=args.password,
                                                port=int(args.port))

        atexit.register(connect.Disconnect, service_instance)
        content = service_instance.RetrieveContent()

        vm = content.searchIndex.FindByUuid(None, args.vm_uuid, True)
        tools_status = vm.guest.toolsStatus
        if (tools_status == 'toolsNotInstalled' or
                tools_status == 'toolsNotRunning'):
            raise SystemExit(
                "VMwareTools is either not running or not installed. "
                "Rerun the script after verifying that VMwareTools "
                "is running")

        creds = vim.vm.guest.NamePasswordAuthentication(
            username=args.vm_user, password=args.vm_pwd
        )

        try:
            pm = content.guestOperationsManager.processManager

            ps = vim.vm.guest.ProcessManager.ProgramSpec(
                programPath=args.path_to_program,
                arguments=args.program_arguments
            )
            res = pm.StartProgramInGuest(vm, creds, ps)

            if res > 0:
                print "Program executed, PID is %d" % res

        except IOError, e:
            print e
    except vmodl.MethodFault as error:
        print "Caught vmodl fault : " + error.msg
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
