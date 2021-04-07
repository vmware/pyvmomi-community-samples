#!/usr/bin/env python
"""
 Written by Michael Rice
 Github: https://github.com/michaelrice
 Website: https://michaelrice.github.io/
 Blog: http://www.errr-online.com/
 This code has been released under the terms of the Apache 2 licenses
 http://www.apache.org/licenses/LICENSE-2.0.html

 Script to quickly get all the VMs with a set of common properties.

"""
from __future__ import print_function
import atexit
from time import clock
from pyVmomi import vim
from tools import cli, service_instance, pchelper

START = clock()


def endit():
    """
    times how long it took for this script to run.

    :return:
    """
    end = clock()
    total = end - START
    print("Completion time: {0} seconds.".format(total))


# List of properties.
# See: http://goo.gl/fjTEpW
# for all properties.
vm_properties = ["name", "config.uuid", "config.hardware.numCPU",
                 "config.hardware.memoryMB", "guest.guestState",
                 "config.guestFullName", "config.guestId",
                 "config.version"]

parser = cli.Parser()
args = parser.get_args()
si = service_instance.connect(args)
atexit.register(endit)

root_folder = si.content.rootFolder
view = pchelper.get_container_view(si, obj_type=[vim.VirtualMachine])
vm_data = pchelper.collect_properties(si,
                                      view_ref=view,
                                      obj_type=vim.VirtualMachine,
                                      path_set=vm_properties,
                                      include_mors=True)
for vm in vm_data:
    print("-" * 70)
    print("Name:                    {0}".format(vm["name"]))
    print("BIOS UUID:               {0}".format(vm["config.uuid"]))
    print("CPUs:                    {0}".format(vm["config.hardware.numCPU"]))
    print("MemoryMB:                {0}".format(
        vm["config.hardware.memoryMB"]))
    print("Guest PowerState:        {0}".format(vm["guest.guestState"]))
    print("Guest Full Name:         {0}".format(vm["config.guestFullName"]))
    print("Guest Container Type:    {0}".format(vm["config.guestId"]))
    print("Container Version:       {0}".format(vm["config.version"]))


print("")
print("Found {0} VirtualMachines.".format(len(vm_data)))
