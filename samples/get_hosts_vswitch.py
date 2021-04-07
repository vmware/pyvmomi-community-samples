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


def get_vm_hosts(content):
    host_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.HostSystem],
                                                        True)
    obj = [host for host in host_view.view]
    host_view.Destroy()
    return obj


def get_hosts_switches(hosts):
    host_switches_dict = {}
    for host in hosts:
        switches = host.config.network.vswitch
        host_switches_dict[host] = switches
    return host_switches_dict


def main():
    parser = cli.Parser()
    args = parser.get_args()
    si = service_instance.connect(args)
    content = si.RetrieveContent()

    hosts = get_vm_hosts(content)
    host_switches_dict = get_hosts_switches(hosts)
    if host_switches_dict is not None:
        print("The vSwitches are:\n")
    for host, vswithes in host_switches_dict.items():
        for v in vswithes:
            print(v.name)


# Main section
if __name__ == "__main__":
    sys.exit(main())
