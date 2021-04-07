#!/usr/bin/env python
"""
Written by nickcooper-zhangtonghao
Github: https://github.com/nickcooper-zhangtonghao
Email: nickcooper-zhangtonghao@opencloud.tech
Note: Example code For testing purposes only
This code has been released under the terms of the Apache-2.0 license
http://opensource.org/licenses/Apache-2.0
"""
from pyVmomi import vim
from tools import service_instance,cli
import sys


def GetVMHosts(content):
    host_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.HostSystem],
                                                        True)
    obj = [host for host in host_view.view]
    host_view.Destroy()
    return obj


def DelHostsPortgroup(hosts, portgroupName):
    for host in hosts:
        host.configManager.networkSystem.RemovePortGroup(portgroupName)
    return True


def DelHostPortgroup(host, portgroupName):
    host.configManager.networkSystem.RemovePortGroup(portgroupName)


def main():
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.PORT_GROUP)
    args = parser.get_args()
    serviceInstance = service_instance.connect(args)
    content = serviceInstance.RetrieveContent()

    hosts = GetVMHosts(content)
    if DelHostsPortgroup(hosts, args.port_group):
        print('Deleted Port Group')


# Main section
if __name__ == "__main__":
    sys.exit(main())
