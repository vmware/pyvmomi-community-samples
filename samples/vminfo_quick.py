"""
 Written by Michael Rice
 Github: https://github.com/michaelrice
 Website: https://michaelrice.github.io/
 Blog: http://www.errr-online.com/
 This code has been released under the terms of the MIT licenses
 http://opensource.org/licenses/MIT

 Script to quickly get all the VMs with a set of common properties.

"""
__author__ = 'errr'

from time import clock
from tools import cli
from tools import pchelper
from pyVim import connect
from pyVmomi import vim

import atexit

START = clock()


def endit():
    """
    times how long it took for this script to run.

    :return:
    """
    end = clock()
    total = end - START
    print "Completion time: {} seconds.".format(total)

# List of properties.
# See: http://vijava.sourceforge.net/vSphereAPIDoc/ver5/ReferenceGuide/vim.VirtualMachine.html
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
except IOError, e:
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
    print "-" * 70
    print "Name:                    {}".format(vm["name"])
    print "BIOS UUID:               {}".format(vm["config.uuid"])
    print "CPUs:                    {}".format(vm["config.hardware.numCPU"])
    print "MemoryMB:                {}".format(vm["config.hardware.memoryMB"])
    print "Guest PowerState:        {}".format(vm["guest.guestState"])
    print "Guest Full Name:         {}".format(vm["config.guestFullName"])
    print "Guest Container Type:    {}".format(vm["config.guestId"])
    print "Container Version:       {}".format(vm["config.version"])


print ""
print "Found {} VirtualMachines.".format(len(vm_data))

