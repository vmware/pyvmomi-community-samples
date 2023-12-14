#!/usr/bin/env python
"""
Written by Maros Kukan
Github: https://github.com/maroskukan
Email: maros.kukan@me.com
Note: Example code For testing purposes only
This code has been released under the terms of the Apache-2.0 license
http://opensource.org/licenses/Apache-2.0
"""

from pyVmomi import vim
from tools import cli, service_instance
import sys


def get_vm_hosts(content):
    host_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.HostSystem],
                                                        True)
    hosts = list(host_view.view)
    host_view.Destroy()
    return hosts


def get_hosts_system_info(hosts):
    host_system_info_dict = {}
    for host in hosts:
        system_info = host.hardware.systemInfo
        host_system_info_dict[host] = system_info
    return host_system_info_dict


def main():
    parser = cli.Parser()
    args = parser.get_args()
    si = service_instance.connect(args)
    content = si.RetrieveContent()

    hosts = get_vm_hosts(content)
    host_system_info_dict = get_hosts_system_info(hosts)
    if host_system_info_dict is not None:
        print("The hosts system info is:\n")
        for host, system_info in host_system_info_dict.items():
            print(f"Host: {host.name}\n")
            print(f"System model identification is {system_info.model}")
            print(f"The serial number is {system_info.serialNumber}")
            print(f"The vendor is {system_info.vendor}")


# Main section
if __name__ == "__main__":
    sys.exit(main())
