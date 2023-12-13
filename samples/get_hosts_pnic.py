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


def get_hosts_pnics(hosts):
    host_pnics_dict = {}
    for host in hosts:
        pnics = host.config.network.pnic
        host_pnics_dict[host] = pnics
    return host_pnics_dict


def main():
    parser = cli.Parser()
    args = parser.get_args()
    si = service_instance.connect(args)
    content = si.RetrieveContent()

    hosts = get_vm_hosts(content)
    host_pnics_dict = get_hosts_pnics(hosts)
    if host_pnics_dict is not None:
        print("Hosts physical network adapters:\n")
        for host, pnics in host_pnics_dict.items():
            print(f"Host: {host.name}\n")
            for pnic in pnics:
                print(pnic.device)
    else:
        print("No physical network adapters found")


# Main section
if __name__ == "__main__":
    sys.exit(main())
