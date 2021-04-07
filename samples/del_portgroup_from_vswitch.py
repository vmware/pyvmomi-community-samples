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
from tools import service_instance, cli


def get_vm_hosts(content):
    host_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.HostSystem],
                                                        True)
    obj = [host for host in host_view.view]
    host_view.Destroy()
    return obj


def del_hosts_portgroup(hosts, portgroup_name):
    for host in hosts:
        host.configManager.networkSystem.RemovePortGroup(portgroup_name)
    return True


def del_host_portgroup(host, portgroup_name):
    host.configManager.networkSystem.RemovePortGroup(portgroup_name)


def main():
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.PORT_GROUP)
    args = parser.get_args()
    si = service_instance.connect(args)
    content = si.RetrieveContent()

    hosts = get_vm_hosts(content)
    if del_hosts_portgroup(hosts, args.port_group):
        print('Deleted Port Group')


# Main section
if __name__ == "__main__":
    sys.exit(main())
