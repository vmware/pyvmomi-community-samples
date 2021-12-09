#!/usr/bin/env python
"""
Written by nickcooper-zhangtonghao
Github: https://github.com/nickcooper-zhangtonghao
Email: nickcooper-zhangtonghao@opencloud.tech
Note: Example code For testing purposes only
This code has been released under the terms of the Apache-2.0 license
http://opensource.org/licenses/Apache-2.0
"""
import sys
from pyVmomi import vim
from tools import cli, service_instance


def get_vm_hosts(content):
    host_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.HostSystem],
                                                        True)
    hosts = list(host_view.view)
    host_view.Destroy()
    return hosts


def del_hosts_switch(hosts, vswitch_name):
    for host in hosts:
        del_host_switch(host, vswitch_name)
    return True


def del_host_switch(host, vswitch_name):
    host.configManager.networkSystem.RemoveVirtualSwitch(vswitch_name)


def main():
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.VSWITCH_NAME)
    args = parser.get_args()
    si = service_instance.connect(args)
    content = si.RetrieveContent()

    hosts = get_vm_hosts(content)
    if del_hosts_switch(hosts, args.vswitch_name):
        print("vSwitch Deleted")


# Main section
if __name__ == "__main__":
    sys.exit(main())
