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


def get_hosts_cpu_info(hosts):
    host_cpu_info_dict = {}
    for host in hosts:
        cpu_info = host.hardware.cpuInfo
        host_cpu_info_dict[host] = cpu_info
    return host_cpu_info_dict


def main():
    parser = cli.Parser()
    args = parser.get_args()
    si = service_instance.connect(args)
    content = si.RetrieveContent()

    hosts = get_vm_hosts(content)
    host_cpu_info_dict = get_hosts_cpu_info(hosts)
    if host_cpu_info_dict is not None:
        print("The hosts cpu info is:\n")
        for host, cpu_info in host_cpu_info_dict.items():
            print(f"Host: {host.name}\n")
            print(f"Number of physical CPU cores on the host is {cpu_info.numCpuCores}")
            print(f"Number of physical CPU packages on the host is {cpu_info.numCpuPackages}")
            print(f"Number of physical CPU threads on the host is {cpu_info.numCpuThreads}")


# Main section
if __name__ == "__main__":
    sys.exit(main())
