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


def get_hosts_mem_size(hosts):
    host_mem_size_dict = {}
    for host in hosts:
        mem_size = host.hardware.memorySize
        host_mem_size_dict[host] = mem_size
    return host_mem_size_dict


def main():
    parser = cli.Parser()
    args = parser.get_args()
    si = service_instance.connect(args)
    content = si.RetrieveContent()

    hosts = get_vm_hosts(content)
    host_mem_size_dict = get_hosts_mem_size(hosts)
    if host_mem_size_dict is not None:
        print("The hosts memory information is:\n")
        for host, mem_size in host_mem_size_dict.items():
            print(f"Host: {host.name}\n")
            print(f"Memory size is {mem_size} bytes")

# Main section
if __name__ == "__main__":
    sys.exit(main())
