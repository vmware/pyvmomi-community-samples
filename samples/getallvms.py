#!/usr/bin/env python
# VMware vSphere Python SDK
# Copyright (c) 2008-2013 VMware, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Python program for listing the vms on an ESX / vCenter host
"""

import atexit

from pyVim import connect
from pyVmomi import vmodl
from os import write

import tools.cli as cli


def print_vm_info(virtual_machine, current_depth=1, max_depth=3):
    """
    Print information for a particular virtual machine or recurse into a
    folder with depth protection
    """
    # if this is a group it will have children. if it does, recurse into them
    # and then return
    if hasattr(virtual_machine, 'childEntity'):
        if current_depth > max_depth:
            return
        children = virtual_machine.childEntity
        for child in children:
            print_vm_info(child, current_depth=current_depth + 1)
        return

    summary = virtual_machine.summary
    try:        
        print "Name       : ", summary.config.name
    except AttributeError:
        return
    print "Path       : ", summary.config.vmPathName
    try:
        print "Guest      : ", summary.config.guestFullName
    except UnicodeEncodeError:
        write(1, "\n")
    print "Instance UUID : ", summary.config.instanceUuid
    print "Bios UUID     : ", summary.config.uuid
    annotation = summary.config.annotation
    if annotation:
        try:
            print "Annotation : ", annotation
        except UnicodeEncodeError:
            write(1, "\n")
    print "State      : ", summary.runtime.powerState
    if summary.guest is not None:
        ip_address = summary.guest.ipAddress
        tools_version = summary.guest.toolsStatus
        if tools_version is not None:
            print "VMware-tools: ", tools_version
        else:
            print "Vmware-tools: None"
        if ip_address:
            print "IP         : ", ip_address
        else:
            print "IP         : None"
    if summary.runtime.question is not None:
        print "Question  : ", summary.runtime.question.text
    write(1, "\n")


def main():
    """
    Simple command-line program for listing the virtual machines on a system.
    """

    args = cli.get_args()

    try:
        service_instance = connect.SmartConnect(host=args.host,
                                                user=args.user,
                                                pwd=args.password,
                                                port=int(args.port))

        atexit.register(connect.Disconnect, service_instance)

        content = service_instance.RetrieveContent()
        folders = content.rootFolder.childEntity
        for sub_folder in folders:
            if hasattr(sub_folder, 'vmFolder'):
                vm_folder = sub_folder.vmFolder
                children = vm_folder.childEntity
                for child in children:
                    print_vm_info(child, max_depth=10)

    except vmodl.MethodFault as error:
        print "Caught vmodl fault : %s" % error.msg
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
