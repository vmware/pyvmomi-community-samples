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

from pyVim import connect
from pyVmomi import vim
from tools import cli
from tools import pchelper

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

args = cli.get_args()
service_instance = None
try:
    service_instance = connect.SmartConnect(host=args.host,
                                            user=args.user,
                                            pwd=args.password,
                                            port=int(args.port))
    atexit.register(connect.Disconnect, service_instance)
    atexit.register(endit)
except IOError as e:
    pass

if not service_instance:
    raise SystemExit("Unable to connect to host with supplied info.")

root_folder = service_instance.content.rootFolder
view = pchelper.get_container_view(service_instance,
                                   obj_type=[vim.VirtualMachine])
vm_data = pchelper.collect_properties(service_instance, view_ref=view,
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
