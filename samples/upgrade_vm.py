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
from tools import cli, service_instance, pchelper


def main():
    """ Upgrades the hardware version of a Virtual Machine. """
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.VM_NAME)
    parser.add_custom_argument('--release', required=False, action='store', default=None,
                                        help='Version/release number of the Virtual machine hardware')
    args = parser.get_args()
    serviceInstance = service_instance.connect(args)

    content = serviceInstance.RetrieveContent()
    vm = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)
    if not vm:
        print("Could not find VM %s" % args.vm_name)
    else:
        print("Upgrading VM %s" % args.vm_name)

        # Set the hardware version to use if specified
        if args.release is not None:
            print("New version will be %s" % args.release)
            version = "vmx-{:02d}".format(args.release)
        else:
            version = None

        # Upgrade the VM
        try:
            task.WaitForTask(task=vm.UpgradeVM_Task(version),
                             si=serviceInstance)
            print("Upgrade complete")
        except vim.fault.AlreadyUpgraded:
            print("VM is already upgraded")


# Start the script
if __name__ == '__main__':
    main()
