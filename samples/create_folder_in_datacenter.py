#!/usr/bin/env python
"""
Written by Chinmaya Bharadwaj
Github: https://github.com/chinmayb/
Example: Create a folder in a datacenter if not exists

"""
from __future__ import print_function

from pyVmomi import vim
from tools import cli, pchelper, service_instance


def create_folder(host_folder, folder_name):
    host_folder.CreateFolder(folder_name)


def main():
    """
    Simple command-line program for creating host and VM folders in a
    datacenter.
    """
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.DATACENTER_NAME, cli.Argument.FOLDER_NAME)
    args = parser.get_args()
    serviceInstance = service_instance.connect(args)

    content = serviceInstance.RetrieveContent()
    dc = pchelper.get_obj(content, [vim.Datacenter], args.datacenter_name)
    if (pchelper.search_for_obj(content, [vim.Folder], args.folder_name)):
        print("Folder '%s' already exists" % args.folder_name)
        return 0
    create_folder(dc.hostFolder, args.folder_name)
    print("Successfully created the host folder '%s'" % args.folder_name)
    create_folder(dc.vmFolder, args.folder_name)
    print("Successfully created the VM folder '%s'" % args.folder_name)
    return 0

# Start program
if __name__ == "__main__":
    main()
