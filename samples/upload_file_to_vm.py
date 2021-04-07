#!/usr/bin/env python
"""
Written by Reubenur Rahman
Github: https://github.com/rreubenur/

This code is released under the terms of the Apache 2
http://www.apache.org/licenses/LICENSE-2.0.html

Example script to upload a file from host to guest

"""
from __future__ import with_statement
import requests
import re
from tools import cli, service_instance, pchelper
from pyVmomi import vim, vmodl


def main():
    """
    Simple command-line program for Uploading a file from host to guest
    """

    parser = cli.Parser()

    parser.add_required_arguments(cli.Argument.VM_USER, cli.Argument.VM_PASS, cli.Argument.REMOTE_FILE_PATH, cli.Argument.LOCAL_FILE_PATH)
    parser.add_optional_arguments(cli.Argument.VM_NAME, cli.Argument.UUID)
    args = parser.get_args()

    vm_path = args.remote_file_path
    try:
        serviceInstance = service_instance.connect(args)
        content = serviceInstance.RetrieveContent()

        vm = None
        if args.uuid:
            search_index = serviceInstance.content.searchIndex
            vm = search_index.FindByUuid(None, args.uuid, True)
        elif args.vm_name:
            content = serviceInstance.RetrieveContent()
            vm = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)

        if not vm:
            raise SystemExit("Unable to locate VirtualMachine.")

        print("Found: {0}".format(vm.name))

        tools_status = vm.guest.toolsStatus
        if (tools_status == 'toolsNotInstalled' or
                tools_status == 'toolsNotRunning'):
            raise SystemExit(
                "VMwareTools is either not running or not installed. "
                "Rerun the script after verifying that VMWareTools "
                "is running")

        creds = vim.vm.guest.NamePasswordAuthentication(
            username=args.vm_user, password=args.vm_pwd)
        with open(args.local_file_path, 'rb') as myfile:
            data_to_send = myfile.read()

        try:
            file_attribute = vim.vm.guest.FileManager.FileAttributes()
            url = content.guestOperationsManager.fileManager. \
                InitiateFileTransferToGuest(vm, creds, vm_path,
                                            file_attribute,
                                            len(data_to_send), True)
            # When : host argument becomes https://*:443/guestFile?
            # Ref: https://github.com/vmware/pyvmomi/blob/master/docs/ \
            #            vim/vm/guest/FileManager.rst
            # Script fails in that case, saying URL has an invalid label.
            # By having hostname in place will take take care of this.
            url = re.sub(r"^https://\*:", "https://"+str(args.host)+":", url)
            resp = requests.put(url, data=data_to_send, verify=False)
            if not resp.status_code == 200:
                print("Error while uploading file")
            else:
                print("Successfully uploaded file")
        except IOError as e:
            print(e)
    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
