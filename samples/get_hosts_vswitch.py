#!/usr/bin/env python
"""
Written by nickcooper-zhangtonghao
Github: https://github.com/nickcooper-zhangtonghao
Email: nickcooper-zhangtonghao@opencloud.tech
Note: Example code For testing purposes only
This code has been released under the terms of the Apache-2.0 license
http://opensource.org/licenses/Apache-2.0
"""

from __future__ import print_function
from pyVmomi import vim
from tools import cli, service_instance
import sys

def GetVMHosts(content):
    host_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.HostSystem],
                                                        True)
    obj = [host for host in host_view.view]
    host_view.Destroy()
    return obj


def GetHostsSwitches(hosts):
    hostSwitchesDict = {}
    for host in hosts:
        switches = host.config.network.vswitch
        hostSwitchesDict[host] = switches
    return hostSwitchesDict


def main():
    parser = cli.Parser()
    args = parser.get_args()
    serviceInstance = service_instance.connect(args)
    content = serviceInstance.RetrieveContent()

    hosts = GetVMHosts(content)
    hostSwitchesDict = GetHostsSwitches(hosts)
    if hostSwitchesDict is not None:
        print("The vSwitches are:\n")
    for host, vswithes in hostSwitchesDict.items():
        for v in vswithes:
            print(v.name)


# Main section
if __name__ == "__main__":
    sys.exit(main())
