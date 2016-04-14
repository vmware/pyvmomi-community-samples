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
import ssl

import requests

from tools import cli
from pyVim import connect
from pyVmomi import vim, vmodl
import ntpath



def get_args():
    """Get command line args from the user.
    """

    parser = cli.build_arg_parser()

    parser.add_argument('-v', '--vm_uuid',
                        required=True,
                        action='store',
                        help='Virtual machine uuid')

    parser.add_argument('-r', '--vm_user',
                        required=True,
                        action='store',
                        help='virtual machine user name')

    parser.add_argument('-w', '--vm_pwd',
                        required=False,
                        action='store',
                        help='virtual machine password')

    parser.add_argument('-t', '--path_to_script',
                        required=True,
                        action='store',
                        help='Local path where the script is')

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
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        service_instance = connect.SmartConnect(host=args.host,
                                                user=args.user,
                                                pwd=args.password,
                                                port=int(args.port),
                                                sslContext=ctx)

        atexit.register(connect.Disconnect, service_instance)
    except:
        print "Unable to connect to %s" % args.host
        exit(1)

    params = {"application_ip": "x.x.x.x", "management_ip": "x.x.x.x", "net_mask": "x.x.x.x", "gateway": "x.x.x.x"}
    runScriptInVM(service_instance, args.vm_uuid, args.vm_user, args.vm_pwd, args.path_to_script, params)


def runScriptInVM(service_instance, vm_uuid, vm_user, vm_pwd, path_to_script, params):
    try:
        content = service_instance.RetrieveContent()

        vm = content.searchIndex.FindByUuid(None, vm_uuid, True)
        tools_status = vm.guest.toolsStatus
        if (tools_status == 'toolsNotInstalled' or
                tools_status == 'toolsNotRunning'):
            raise SystemExit(
                "VMwareTools is either not running or not installed. "
                "Rerun the script after verifying that VMwareTools "
                "is running")

        script = open(path_to_script, 'rb')
        path_on_vm = "/tmp/%s" % ntpath.basename(script.name)

        vm_shell = script.readline().replace("#!", "").rstrip()
        script.seek(0)
        contents = script.read() % params
        # contents += "\nrm $0"


        creds = vim.vm.guest.NamePasswordAuthentication(
            username=vm_user, password=vm_pwd
        )

        try:
            file_attribute = vim.vm.guest.FileManager.FileAttributes()
            url = content.guestOperationsManager.fileManager. \
                InitiateFileTransferToGuest(vm, creds, path_on_vm,
                                            file_attribute,
                                            len(contents), True)
            resp = requests.put(url, data=contents, verify=False)
            if not resp.status_code == 200:
                print "Error while uploading file"
            else:
                print "Successfully uploaded file"
        except IOError, e:
            print e

        try:
            pm = content.guestOperationsManager.processManager

            ps = vim.vm.guest.ProcessManager.ProgramSpec(
                programPath=vm_shell,
                arguments=path_on_vm
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
