#!/usr/bin/env python
# VMware vSphere Python SDK
# Copyright (c) 2008-2014 VMware, Inc. All Rights Reserved.
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
from __future__ import print_function

import atexit
import argparse
import getpass

from pyVim import connect

# Demonstrates:
# =============
# * How to write python 2.7 and 3.3 compatible code in one script
# * How to parse arguments in a python script
# * How to pretty print format a dictionary
# * How to connect to a vSphere instance
# * How to search for virtual machines efficiently
# * How to interrogate virtual machine hardware info
# * How to determine the data type of a dynamic object instance
# * How to build a summary of a virtual device & virtual disk
# * How to interrogate a datastore and its hosts mounts
#
# Not shown, how to ask a datastore for all the virtual machines it 'owns'
#
# Sample output:
#
# $ virtual_machine_device_info.py -s vcsa -u my_user -i 172.16.254.101
#
# Found Virtual Machine
# =====================
#   guest OS name            : Ubuntu Linux (64-bit)
#   name                     : box
#   last booted timestamp    : 2014-10-13 01:45:57.647340+00:00
#   bios UUID                : 420264ab-848b-1586-b589-b9bd3a71b3aa
#   path to VM               : [storage0] box/box.vmx
#   guest OS id              : ubuntu64Guest
#   host name                : esx_host_01
#   instance UUID            : 500221fe-3473-60ff-fab2-1811600208a0
#   Devices:
#   --------
#   label: IDE 0
#   ------------------
#     device type    : vim.vm.device.VirtualIDEController
#     backing type   : NoneType
#     key            : 200
#     summary        : IDE 0
#   label: IDE 1
#   ------------------
#     device type    : vim.vm.device.VirtualIDEController
#     backing type   : NoneType
#     key            : 201
#     summary        : IDE 1
#   label: PS2 controller 0
#   ------------------
#     device type    : vim.vm.device.VirtualPS2Controller
#     backing type   : NoneType
#     key            : 300
#     summary        : PS2 controller 0
#   label: PCI controller 0
#   ------------------
#     device type    : vim.vm.device.VirtualPCIController
#     backing type   : NoneType
#     key            : 100
#     summary        : PCI controller 0
#   label: SIO controller 0
#   ------------------
#     device type    : vim.vm.device.VirtualSIOController
#     backing type   : NoneType
#     key            : 400
#     summary        : SIO controller 0
#   label: Keyboard
#   ------------------
#     device type    : vim.vm.device.VirtualKeyboard
#     backing type   : NoneType
#     key            : 600
#     summary        : Keyboard
#   label: Pointing device
#   ------------------
#     device type    : vim.vm.device.VirtualPointingDevice
#     backing type   : vim.vm.device.VirtualPointingDevice.DeviceBackingInfo
#     key            : 700
#     summary        : Pointing device; Device
#   ------------------
#   label: Video card
#   ------------------
#     device type    : vim.vm.device.VirtualVideoCard
#     backing type   : NoneType
#     key            : 500
#     summary        : Video card
#   label: VMCI device
#   ------------------
#     device type    : vim.vm.device.VirtualVMCIDevice
#     backing type   : NoneType
#     key            : 12000
#     summary        : Device on the virtual machine PCI bus that provides supp
#   label: SCSI controller 0
#   ------------------
#     device type    : vim.vm.device.VirtualLsiLogicController
#     backing type   : NoneType
#     key            : 1000
#     summary        : LSI Logic
#   label: Hard disk 1
#   ------------------
#     device type    : vim.vm.device.VirtualDisk
#     backing type   : vim.vm.device.VirtualDisk.FlatVer2BackingInfo
#     key            : 2000
#     summary        : 16,777,216 KB
#     datastore
#         name: storage0
#         host: esx_host_01
#         summary
#             url: ds:///vmfs/volumes/501fa6d9-8907f56a-fa19-782bcb74158e/
#             freeSpace: 5750390784
#             file system: VMFS
#             capacity: 494726545408
#     fileName: [storage0] box/box.vmdk
#     device ID: None
#   ------------------
#   label: CD/DVD drive 1
#   ------------------
#     device type    : vim.vm.device.VirtualCdrom
#     backing type   : vim.vm.device.VirtualCdrom.AtapiBackingInfo
#     key            : 3002
#     summary        : ATAPI /vmfs/devices/cdrom/mpx.vmhba0:C0:T0:L0
#   ------------------
#   label: Network adapter 1
#   ------------------
#     device type    : vim.vm.device.VirtualE1000
#     backing type   : vim.vm.device.VirtualEthernetCard.NetworkBackingInfo
#     key            : 4000
#     summary        : VM Network
#   ------------------
#   label: Floppy drive 1
#   ------------------
#     device type    : vim.vm.device.VirtualFloppy
#     backing type   : vim.vm.device.VirtualFloppy.RemoteDeviceBackingInfo
#     key            : 8000
#     summary        : Remote
#   ------------------
# =====================


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='Remote host to connect to')

    parser.add_argument('-o', '--port',
                        required=False,
                        action='store',
                        help="port to use, default 443", default=443)

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='User name to use when connecting to host')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to use when connecting to host')

    parser.add_argument('-d', '--uuid',
                        required=False,
                        action='store',
                        help='Instance UUID (not BIOS id) of a VM to find.')

    parser.add_argument('-i', '--ip',
                        required=False,
                        action='store',
                        help='IP address of the VM to search for')

    args = parser.parse_args()

    password = None
    if args.password is None:
        password = getpass.getpass(
            prompt='Enter password for host %s and user %s: ' %
                   (args.host, args.user))

    args = parser.parse_args()

    if password:
        args.password = password

    return args

args = get_args()

# form a connection...
si = connect.SmartConnect(host=args.host, user=args.user, pwd=args.password,
                          port=args.port)

# Note: from daemons use a shutdown hook to do this, not the atexit
atexit.register(connect.Disconnect, si)

# http://pubs.vmware.com/vsphere-55/topic/com.vmware.wssdk.apiref.doc/vim.SearchIndex.html
search_index = si.content.searchIndex

# without exception find managed objects using durable identifiers that the
# search index can find easily. This is much better than caching information
# that is non-durable and potentially buggy.

vm = None
if args.uuid:
    vm = search_index.FindByUuid(None, args.uuid, True, True)
elif args.ip:
    vm = search_index.FindByIp(None, args.ip, True)

if not vm:
    print(u"Could not find a virtual machine to examine.")
    exit(1)

print(u"Found Virtual Machine")
print(u"=====================")
details = {'name': vm.summary.config.name,
           'instance UUID': vm.summary.config.instanceUuid,
           'bios UUID': vm.summary.config.uuid,
           'path to VM': vm.summary.config.vmPathName,
           'guest OS id': vm.summary.config.guestId,
           'guest OS name': vm.summary.config.guestFullName,
           'host name': vm.runtime.host.name,
           'last booted timestamp': vm.runtime.bootTime}

for name, value in details.items():
    print(u"  {0:{width}{base}}: {1}".format(name, value, width=25, base='s'))

print(u"  Devices:")
print(u"  --------")
for device in vm.config.hardware.device:
    # diving into each device, we pull out a few interesting bits
    dev_details = {'key': device.key,
                   'summary': device.deviceInfo.summary,
                   'device type': type(device).__name__,
                   'backing type': type(device.backing).__name__}

    print(u"  label: {0}".format(device.deviceInfo.label))
    print(u"  ------------------")
    for name, value in dev_details.items():
        print(u"    {0:{width}{base}}: {1}".format(name, value,
                                                   width=15, base='s'))

    if device.backing is None:
        continue

    # the following is a bit of a hack, but it lets us build a summary
    # without making many assumptions about the backing type, if the
    # backing type has a file name we *know* it's sitting on a datastore
    # and will have to have all of the following attributes.
    if hasattr(device.backing, 'fileName'):
            datastore = device.backing.datastore
            if datastore:
                print(u"    datastore")
                print(u"        name: {0}".format(datastore.name))
                # there may be multiple hosts, the host property
                # is a host mount info type not a host system type
                # but we can navigate to the host system from there
                for host_mount in datastore.host:
                    host_system = host_mount.key
                    print(u"        host: {0}".format(host_system.name))
                print(u"        summary")
                summary = {'capacity': datastore.summary.capacity,
                           'freeSpace': datastore.summary.freeSpace,
                           'file system': datastore.summary.type,
                           'url': datastore.summary.url}
                for key, val in summary.items():
                    print(u"            {0}: {1}".format(key, val))
            print(u"    fileName: {0}".format(device.backing.fileName))
            print(u"    device ID: {0}".format(device.backing.backingObjectId))

    print(u"  ------------------")

print(u"=====================")
exit()
