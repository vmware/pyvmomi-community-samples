#!/usr/bin/env python

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

# Written by Jason Cohen
# Based on:
# https://github.com/lamw/vghetto-scripts/blob/master/powershell/MacLearn.ps1

# This script will enable  the MAC Learning capability for DistributedPortGroup
# on vSphere 6.7+


from __future__ import print_function
from pyVim.task import WaitForTask
from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect
from pyVmomi import vim, vmodl
import atexit
import argparse
import getpass


def get_args():
    parser = argparse.ArgumentParser(
        description="Arguments for talking to vCenter"
    )

    parser.add_argument(
        "-k",
        "--disable_ssl_verification",
        required=False,
        action="store_true",
        help="Disable ssl host certificate verification",
    )

    parser.add_argument(
        "-l",
        "--enable_mac_learning",
        required=False,
        action="store_true",
        help="Enable MAC learning on the specified DVS PortGroup.",
    )

    parser.add_argument(
        "-u", "--user", required=True, action="store", help="User name to use"
    )

    parser.add_argument(
        "-p",
        "--password",
        required=False,
        action="store",
        help="Password to use",
    )

    parser.add_argument(
        "host", action="store", help="vSpehre host[:port] to connect to"
    )

    parser.add_argument(
        "dvportgroup",
        action="store",
        help="Name of the DVS PortGroup. Use 'all' to modify all Port Groups",
    )

    args = parser.parse_args()
    return args


def get_obj(content, vimtype, name=None, folder=None, recurse=True):
    if not folder:
        folder = content.rootFolder

    obj = None
    container = content.viewManager.CreateContainerView(
        folder, vimtype, recurse
    )
    if not name:
        obj = {}
        for managed_object_ref in container.view:
            obj.update({managed_object_ref: managed_object_ref.name})
    else:
        obj = None
        for c in container.view:
            if c.name == name:
                obj = c
                break

    return obj


def main():
    args = get_args()
    host_port = args.host.split(":")

    if len(host_port) == 1:
        host = host_port[0]
        port = 443
    elif len(host_port) == 2:
        host = host_port[0]
        port = int(host_port[1])
    else:
        print("Invalid host specified: ", args.host)
        return -1

    if args.password:
        password = args.password
    else:
        password = getpass.getpass(
            prompt="Enter password for host %s and "
            "user %s: " % (args.host, args.user)
        )
    try:
        if args.disable_ssl_verification:
            si = SmartConnectNoSSL(
                host=host, user=args.user, pwd=password, port=port
            )
        else:
            si = SmartConnect(
                host=host, user=args.user, pwd=password, port=port
            )
    except vmodl.MethodFault as e:
        print(e.msg)
        return -1

    atexit.register(Disconnect, si)

    content = si.RetrieveContent()

    if args.dvportgroup == "all":
        dpg_list = get_obj(content, [vim.dvs.DistributedVirtualPortgroup])
    else:
        pg = get_obj(
            content, [vim.dvs.DistributedVirtualPortgroup], args.dvportgroup
        )
        if pg is None:
            print("Failed to find the dvportgroup %s" % args.dvportgroup)
            return 0
        else:
            dpg_list = [pg]

    for dpg in dpg_list:
        if not dpg.config.uplink:
            spec = vim.dvs.DistributedVirtualPortgroup.ConfigSpec()
            setting = (
                vim.dvs.VmwareDistributedVirtualSwitch.VmwarePortConfigPolicy()
            )
            mmp = vim.dvs.VmwareDistributedVirtualSwitch.MacManagementPolicy()
            mlp = vim.dvs.VmwareDistributedVirtualSwitch.MacLearningPolicy()
            mmp.macLearningPolicy = mlp
            setting.macManagementPolicy = mmp
            spec.defaultPortConfig = setting
            spec.configVersion = dpg.config.configVersion

        if args.enable_mac_learning:
            mmp.allowPromiscuous = False
            mmp.forgedTransmits = True
            mmp.macChanges = True
            mlp.enabled = True
            mlp.allowUnicastFlooding = True
            mlp.limitPolicy = "DROP"
            mlp.limit = 4096
            try:
                WaitForTask(dpg.ReconfigureDVPortgroup_Task(spec))
            except vmodl.MethodFault as e:
                print(e.msg)
                return -1
        else:
            mmp.allowPromiscuous = False
            mmp.forgedTransmits = False
            mmp.macChanges = False
            mlp.enabled = False
            try:
                WaitForTask(dpg.ReconfigureDVPortgroup_Task(spec))
            except vmodl.MethodFault as e:
                print(e.msg)
                return -1


if __name__ == "__main__":
    main()
