#!/usr/bin/env python
#
# Written by Amdei The Botan
# GitHub: https://github.com/amdei
# Email: amdeich@gmail.com
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
Python program for listing the VM network interfaces (NIC) on an ESX / vCenter host
"""

import re
from pyVmomi import vmodl, vim
from tools import cli, service_instance, pchelper


def get_all_dvs(content, datacenter):
    dvs_lists = pchelper.get_all_obj(
        content, [vim.DistributedVirtualSwitch], folder=datacenter.networkFolder)
    return list(dvs_lists)


def create_pg_dvs_map(dvs_list):
    """
    Create a map of PortGroup key to a PortGroup name for faster lookups
    """
    pg_dvs_map = {}
    for dvs in dvs_list:
        for dvs_pg in dvs.portgroup:
            # Here we assume that PortGroup key is unique across all DVSs
            pg_dvs_map[dvs_pg.key] = dvs.name + '/' + dvs_pg.name

    return pg_dvs_map


def get_netdev_pg_name(pg_key, dvs_pg):
    pgn = dvs_pg.get(pg_key, 'WTF!?!')
    return pgn


def print_vm_info(virtual_machine, dvs_pg):
    """
    Print information for a particular virtual machine
    """
    summary = virtual_machine.summary
    print("VM Name    : ", summary.config.name)
    print("Path       : ", summary.config.vmPathName)
    print("Guest      : ", summary.config.guestFullName)

    dev_ether = vim.vm.device.VirtualEthernetCard
    net_b_info = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo
    dvp_b_info = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo
    for dev in virtual_machine.config.hardware.device:
        if isinstance(dev, dev_ether):
            connected_to = '<undetermined>'
            if isinstance(dev.backing, net_b_info):
                # Simple Virtual Switch
                connected_to = dev.backing.deviceName
            elif isinstance(dev.backing, dvp_b_info):
                # Distributed Virtual Switch
                connected_to = get_netdev_pg_name(dev.backing.port.portgroupKey, dvs_pg)
            else:
                # Please contact developers if you happen to see it
                print('Add handling of ', type(dev.backing), '!')
            print(dev.deviceInfo.label, "->", connected_to)
    print("")


def main():
    """
    Command-line program for listing the virtual machines NICs on a system.
    """

    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.DATACENTER_NAME)
    parser.add_custom_argument('-f', '--find', required=False,
                               action='store', help='String to match VM names')
    parser.add_custom_argument('--sort', required=False,
                               action='store_true', help='Sort VM names alphabetically')

    args = parser.get_args()
    si = service_instance.connect(args)

    try:
        content = si.RetrieveContent()

        datacenter = pchelper.get_obj(content, [vim.Datacenter], args.datacenter_name)

        if datacenter is None:
            print("Failed to find the datacenter %s" % args.datacenter_name)
            return 3

        dvs_list = get_all_dvs(content, datacenter)
        dvs_pg = create_pg_dvs_map(dvs_list)

        container = content.rootFolder  # starting point to look into
        view_type = [vim.VirtualMachine]  # object types to look for
        recursive = True  # whether we should look into it recursively
        container_view = content.viewManager.CreateContainerView(
            container, view_type, recursive)

        children = container_view.view

        if args.find is not None:
            pat = re.compile(args.find, re.IGNORECASE)
            children = list(filter(lambda child: pat.search(child.summary.config.name), children))
        if args.sort is not None:
            children.sort(key=lambda child: child.summary.config.name)

        print('Datacenter Name'.ljust(40) + ' :', args.datacenter_name)
        print(40 * '#')
        for child in children:
            print_vm_info(child, dvs_pg)

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
