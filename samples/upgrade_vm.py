#!/usr/bin/env python

"""
Upgrades the hardware version of a Virtual Machine.

Written by Christopher Goes
GitHub: https://github.com/GhostofGoes/

Sample based on code found here: https://github.com/GhostofGoes/ADLES

This code is released under the terms of the Apache 2
http://www.apache.org/licenses/LICENSE-2.0.html

Example:

python upgrade_vm.py
    -h <vsphere host>
    -o <port>
    -u <username>
    -p <password>
    -n <vm name>
    -v <version to upgrade to>

If version is not specified, the default of the highest version
the host supports is used.
"""

from __future__ import print_function
import atexit

from pyVim import connect, task
from pyVmomi import vim

from tools import cli


def get_args():
    """ Get commandline arguments from the user. """
    parser = cli.build_arg_parser()

    parser.add_argument('-v', '--version',
                        required=False,
                        action='store',
                        default=None,
                        help='Virtual machine hardware version')
    parser.add_argument('-n', '--name',
                        required=True,
                        action='store',
                        help='Name of the virtual machine to upgrade '
                             '(case sensitive!)')
    parser.add_argument('-S', '--use-ssl',
                        required=False,
                        action='store_true',
                        default=False,  # Test setups are usually self-signed
                        help='Enable SSL host certificate verification')

    args = parser.parse_args()
    cli.prompt_for_password(args)
    return args


def get_vm(content, name):
    """ Gets a named virtual machine. """
    virtual_machine = None
    container = content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.VirtualMachine],
                                                        True)
    for item in container.view:
        if item.name == name:
            virtual_machine = item
            break
    container.Destroy()  # Best practice. Frees up resources on host.
    return virtual_machine


def connect_vsphere(username, password, hostname, port, use_ssl):
    """ Connects to a ESXi host or vCenter server. """
    server = None
    try:
        if use_ssl:  # Connect to server using SSL certificate verification
            server = connect.SmartConnect(host=hostname, user=username,
                                          pwd=password, port=port)
        else:
            server = connect.SmartConnectNoSSL(host=hostname, user=username,
                                               pwd=password, port=port)
    except vim.fault.InvalidLogin:
        print("ERROR: Invalid login credentials for user '%s'" % username)
        exit(1)
    except vim.fault as message:
        print("Error connecting to vSphere: %s" % str(message))
        exit(1)

    # Ensures clean disconnect upon program termination
    atexit.register(connect.Disconnect, server)

    return server


def main():
    """ Upgrades the hardware version of a Virtual Machine. """
    args = get_args()
    service_instance = connect_vsphere(args.user, args.password,
                                       args.host, int(args.port), args.use_ssl)

    content = service_instance.RetrieveContent()
    virtual_machine = get_vm(content, args.name)
    if not virtual_machine:
        print("Could not find VM %s" % args.name)
    else:
        print("Upgrading VM %s" % args.name)

        # Set the hardware version to use if specified
        if args.version is not None:
            print("New version will be %s" % args.version)
            version = "vmx-{:02d}".format(args.version)
        else:
            version = None

        # Upgrade the VM
        try:
            task.WaitForTask(task=virtual_machine.UpgradeVM_Task(version),
                             si=service_instance)
        except vim.fault.AlreadyUpgraded:
            print("VM is already upgraded")


# Start the script
if __name__ == '__main__':
    main()
