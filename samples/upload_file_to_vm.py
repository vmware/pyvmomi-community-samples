#!/usr/bin/env python
"""
Written by Reubenur Rahman
Github: https://github.com/rreubenur/

This code is released under the terms of the Apache 2
http://www.apache.org/licenses/LICENSE-2.0.html

Example script to upload a file from host to guest

"""
from __future__ import with_statement
import atexit
import requests
from tools import cli
from tools import tasks
from pyVim import connect
from pyVmomi import vim, vmodl
import re


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

    parser.add_argument('-l', '--path_inside_vm',
                        required=False,
                        action='store',
                        help='Path inside VM for upload')

    parser.add_argument('-f', '--upload_file',
                        required=False,
                        action='store',
                        help='Path of the file to be uploaded from host')

    args = parser.parse_args()

    cli.prompt_for_password(args)
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

        vm = content.searchIndex.FindByUuid(None, args.vm_uuid, True)
        tools_status = vm.guest.toolsStatus
        if (tools_status == 'toolsNotInstalled' or
                tools_status == 'toolsNotRunning'):
            raise SystemExit(
                "VMwareTools is either not running or not installed. "
                "Rerun the script after verifying that VMWareTools "
                "is running")

        creds = vim.vm.guest.NamePasswordAuthentication(
            username=args.vm_user, password=args.vm_pwd)
        with open(args.upload_file, 'rb') as myfile:
            fileinmemory = myfile.read()

        try:
            file_attribute = vim.vm.guest.FileManager.FileAttributes()
            url = content.guestOperationsManager.fileManager. \
                InitiateFileTransferToGuest(vm, creds, vm_path,
                                            file_attribute,
                                            len(fileinmemory), True)
            # When : host argument becomes https://*:443/guestFile?
            # Ref: https://github.com/vmware/pyvmomi/blob/master/docs/ \
            #            vim/vm/guest/FileManager.rst
            # Script fails in that case, saying URL has an invalid label.
            # By having hostname in place will take take care of this.
            url = re.sub(r"^https://\*:", "https://"+str(args.host)+":", url)
            resp = requests.put(url, data=fileinmemory, verify=False)
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
