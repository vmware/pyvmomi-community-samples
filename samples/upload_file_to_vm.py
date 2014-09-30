"""
Written by Reubenur Rahman
Github: https://github.com/rreubenur/

This code is released under the terms of the Apache 2
http://www.apache.org/licenses/LICENSE-2.0.html

Example script to change the network of the Virtual Machine NIC

"""
from __future__ import with_statement
import atexit
import getpass
import requests
from tools import cli
from tools import tasks
from pyVim import connect
from pyVmomi import vim, vmodl


def get_args():
    """Get command line args from the user.
    """

    parser = cli.build_arg_parser()
    parser.add_argument('-c', '--datacenter',
                        required=False,
                        action='store',
                        help='Datacenter Name')

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

    parser.add_argument('-l', '--path_inside_vm',
                        required=False,
                        action='store',
                        help='Path inside VM for upload')

    parser.add_argument('-f', '--upload_file',
                        required=False,
                        action='store',
                        help='Path of the file to be uploaded from host')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password for host %s and user %s: ' %
                   (args.host, args.user))
    return args


def main():
    """
    Simple command-line program for Uploading a file from host to guest
    """

    args = get_args()
    vm_path = args.path_inside_vm
    try:
        service_instance = connect.SmartConnect(host=args.host,
                                                user=args.user,
                                                pwd=args.password,
                                                port=int(args.port))

        atexit.register(connect.Disconnect, service_instance)
        content = service_instance.RetrieveContent()

        for child in content.rootFolder.childEntity:
            if hasattr(child, 'hostFolder'):
                datacenter = child
                if datacenter.name == args.datacenter:
                    break
        vm = content.searchIndex.FindByUuid(datacenter, args.vm_uuid, True)
        creds = vim.vm.guest.NamePasswordAuthentication(
            username=args.vm_user, password=args.vm_pwd)
        with open(args.upload_file, 'r') as myfile:
            args = myfile.read()

        try:
            file_attribute = vim.vm.guest.FileManager.FileAttributes()
            url = content.guestOperationsManager.fileManager.InitiateFileTransferToGuest(
                vm, creds, vm_path, file_attribute, len(args), True)
            resp = requests.put(url, data=args, verify=False)
            if not resp.status_code == 200:
                print "Error while uploading file"
            else:
                print "Successfully uploaded file"
        except IOError, e:
            print e
    except vmodl.MethodFault as error:
        print "Caught vmodl fault : " + error.msg
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
