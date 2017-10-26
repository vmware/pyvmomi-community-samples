#!/usr/bin/env python
"""
Written by Chinmaya Bharadwaj
Github: https://github.com/chinmayb/
Example: Create a folder in a datacenter if not exists

"""
from __future__ import print_function

from pyVmomi import vim

from pyVim.connect import SmartConnect, Disconnect

import argparse
import atexit
import getpass


def GetArgs():
    """
    Supports the command-line arguments listed below.
    """
    parser = argparse.ArgumentParser(
        description='Process args for retrieving all the Virtual Machines')
    parser.add_argument('-s', '--host', required=True, action='store',
                        help='Remote host to connect to')
    parser.add_argument('-o', '--port', type=int, default=443, action='store',
                        help='Port to connect on')
    parser.add_argument('-u', '--user', required=True, action='store',
                        help='User name to use when connecting to host')
    parser.add_argument('-p', '--password', required=False, action='store',
                        help='Password to use when connecting to host')
    parser.add_argument('-d', '--datacenter', required=True,
                        help='name of the datacenter'),
    parser.add_argument('-f', '--folder', required=True,
                        help='name of the folder')
    args = parser.parse_args()
    return args


def get_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def create_folder(content, host_folder, folder_name):
    host_folder.CreateFolder(folder_name)


def main():
    """
    Simple command-line program for creating host and VM folders in a
    datacenter.
    """
    args = GetArgs()
    if args.password:
        password = args.password
    else:
        password = getpass.getpass(prompt='Enter password for host %s and '
                                   'user %s: ' % (args.host, args.user))

    si = SmartConnect(host=args.host,
                      user=args.user,
                      pwd=password,
                      port=int(args.port))
    if not si:
        print("Could not connect to the specified host using specified "
              "username and password")
        return -1

    atexit.register(Disconnect, si)

    content = si.RetrieveContent()
    dc = get_obj(content, [vim.Datacenter], args.datacenter)
    if (get_obj(content, [vim.Folder], args.folder)):
        print("Folder '%s' already exists" % args.folder)
        return 0
    create_folder(content, dc.hostFolder, args.folder)
    print("Successfully created the host folder '%s'" % args.folder)
    create_folder(content, dc.vmFolder, args.folder)
    print("Successfully created the VM folder '%s'" % args.folder)
    return 0

# Start program
if __name__ == "__main__":
    main()
