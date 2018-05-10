#!/usr/bin/env python

import atexit
import sys
import getopt
import ssl
import subprocess

from pyVmomi import vim, vmodl
from pyVim.task import WaitForTask
from pyVim import connect
from pyVim.connect import Disconnect, SmartConnect, GetSi

"""
This interactive script allows you to revert multiple VMs to
their respective snapshots from the CLI.

INSTRUCTIONS:
- Install pyVmomi module on your local environment: 'pip install pyVmomi'
- Copy this file to your local environment
- Change the vSphere credentials in this file according to your environment
- 'cd' to  directory on your local machine where this file is located
- Execute the script: 'python2.7 revert_multiple_vms.py'
- Follow the prompts

Author: Ty Hitzeman (https://github.com/tyler-hitzeman)
Inspired by Abdul Anshad's script:
https://github.com/vmware/pyvmomi-community-samples/blob/master/samples/snapshot_operations.py

This code has been released under the terms of the Apache-2.0 license
http://opensource.org/licenses/Apache-2.0
"""

# vSphere credentials. This script is flexible enough to
# accomodate multiple vSphere hosts in your network,
# but it should also work fine if there is only one vSphere host.
vsphere1_ip = "IP address of your vSphere host"  # Ex: 192.168.1.100
vsphere1_user = "Admin user of your vSphere host"  # Ex: admin@server.com
vsphere1_pw = "Admin user's password"

vsphere2_ip = "IP address of your second vSphere host"  # Ex: 192.168.2.100
vsphere2_user = "Admin user of your second vSphere host"
vsphere2_pw = "Admin user's password"

host = ""
vm_list = []

# Initialize variables used to authenticate to vSphere
ssl_enabled = False
service_instance = None
context = None  # SSL context


# Start of script
def main(argv):
    get_user_input()


def get_user_input():

    # Get subnet
    subnet = raw_input("Are you reverting VMs on the .1 or .2 subnet? ")

    if subnet == ".1":
        host = vsphere1_ip
        user = vsphere1_user
        password = vsphere1_pw
    elif subnet == ".2":
        host = vsphere2_ip
        user = vsphere2_user
        password = vsphere2_pw
    else:
        print """
        Error: Invalid subnet!
        Enter '.1' if your VM's IP starts with 192.168.1, or
        '.2' if your VM's IP starts with 192.168.2
        """
        get_user_input()

    if ssl_enabled is False and hasattr(ssl, "_create_unverified_context"):
        context = ssl._create_unverified_context()

    service_instance = connect.Connect(host, 443,
                         user, password,
                         sslContext=context)

    # The 'name' of a VM is the one that appears in vSphere. Ex: 'Ubuntu_Ty_1'
    print(
        '''
        Type the full name of the VM(s) you'd like to revert on the %s subnet,
        then press ENTER to go to the next line and repeat.
        Press ENTER twice when finished.
        Be sure that none of the lines contain trailing spaces.
        \n
        '''
        % subnet
    )

    # Append each VM name to a list. List is complete after user RETURNs an empty line.
    lines = []
    full_list = False

    while not full_list:
        line = raw_input()
        if line:
            lines.append(line)
        elif line == "":
            multi_line_list = '\n'.join(lines)
            full_list = True
        else:
            print """
            Something went wrong. Each line should be a name of the VM as it appears in vSphere. For example:

            Ubuntu_Ty_1
            Ubuntu_Ty_2
            Ubuntu_Ty_3

            Please try again.
            """
            get_user_input()

    # Convert list to map so we can split it up and iterate through it
    vm_names_list = map(str, multi_line_list.split())

    # Get name of snapshot. All VMs in group must have same snapshot
    snapshot_name_from_user = raw_input("What is the name of the snapshot name that you want to revert the above VMs to? ")
    snapshot_name = snapshot_name_from_user

    confirm = raw_input("Are you sure you want to revert the above VMs to their %s snapshot? [y/n]: " % snapshot_name_from_user)

    if confirm == "y" in confirm or "yes" in confirm:
        print "\n Cool beans! \n"
    elif confirm == "n" in confirm or "no" in confirm:
        print "Let's try again"
        get_user_input()
    else:
        print "\n Must enter 'y' or 'n'\n"
        get_user_input()

    # Now that you have all required info from the user, call function to start reverting to snapshot
    revert_to_snapshot(vm_names_list, snapshot_name, service_instance)


"""
Use the user-provided info to connect to vSphere and revert the given VM to their BaseInstall snapshot.
"""


def revert_to_snapshot(vm_names_list, snapshot_name, service_instance):
    # Connect to vSphere and start reverting
    content = service_instance.RetrieveContent()

    for vm in vm_names_list:
        vm_name = vm

        # Get official VM name
        vm = get_vm_object(content, [vim.VirtualMachine], vm_name)

        # Notify user if vm_object wasn't found
        if not vm:
            print("%s was not found. \n This error could occur if 1) the VM doesn't exists, 2) you're using the wrong subnet, or 3) something is wrong with this script" % vm_name)
            sys.exit()

        # Call the function that retrieves the object of the snapshot, providing the official snapshot name & user-friendly snapshot name as arguments
        snap_object = get_snapshot_object_from_name(vm.snapshot.rootSnapshotList, snapshot_name)

        # Once you have the official snapshot object, revert to it for the given VM
        if len(snap_object) == 1:
            snap_object = snap_object[0].snapshot
            print("Reverting %s to snapshot %s ..." % (vm_name, snapshot_name))
            WaitForTask(snap_object.RevertToSnapshot_Task())
            print("\t Success \n")
        else:
            print("No snapshots found with name: %s on VM: %s" % (snapshot_name, vm.name))

    # Log out of vSphere after reverting all VMs to their snapshots
    atexit.register(Disconnect, service_instance)

    # Terminate this script
    sys.exit()


"""
Get the VM object from vSphere associated with its name
"""


def get_vm_object(content, vimtype, name):
    vm_object = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            vm_object = c
            break
    return vm_object


"""
Get the snapshot object from vSphere associated with its name
"""


def get_snapshot_object_from_name(snapshot_list, official_snapshot):
    snap_obj = []

    # Get the correct snapshot object for the given name
    for snapshot in snapshot_list:
        if snapshot.name == official_snapshot:
            snap_obj.append(snapshot)
        else:
            snap_obj = snap_obj + get_snapshot_object_from_name(snapshot.childSnapshotList, official_snapshot)
    return snap_obj


# Start program
if __name__ == "__main__":
    main(sys.argv[1:])