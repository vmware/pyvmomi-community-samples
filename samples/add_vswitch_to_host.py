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


def add_hosts_switch(hosts, vswitch_name):
    for host in hosts:
        add_host_switch(host, vswitch_name)
    return True


def add_host_switch(host, vswitch_name):
    vswitch_spec = vim.host.VirtualSwitch.Specification()
    vswitch_spec.numPorts = 1024
    vswitch_spec.mtu = 1450
    host.configManager.networkSystem.AddVirtualSwitch(vswitch_name, vswitch_spec)


def main():
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.VSWITCH_NAME)
    args = parser.get_args()
    si = service_instance.connect(args)
    content = si.RetrieveContent()

    hosts = get_vm_hosts(content)
    if add_hosts_switch(hosts, args.vswitch_name):
        print("vSwitch Added")


# Main section
if __name__ == "__main__":
    sys.exit(main())
