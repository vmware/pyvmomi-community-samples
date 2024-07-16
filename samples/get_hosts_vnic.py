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


def get_hosts_vnics(hosts):
    host_vnics_dict = {}
    for host in hosts:
        vnics = host.config.network.vnic
        host_vnics_dict[host] = vnics
    return host_vnics_dict


def main():
    parser = cli.Parser()
    args = parser.get_args()
    si = service_instance.connect(args)
    content = si.RetrieveContent()

    hosts = get_vm_hosts(content)
    host_vnics_dict = get_hosts_vnics(hosts)
    if host_vnics_dict is not None:
        print("Hosts virtual network adapters:\n")
        for host, vnics in host_vnics_dict.items():
            print(f"Host: {host.name}\n")
            for vnic in vnics:
                    print(f"Device is {vnic.device}")
                    print(f"Portgroup is {vnic.portgroup}")
                    print(f"IP address is {vnic.spec.ip.ipAddress}")
                    print(f"Subnet mask is {vnic.spec.ip.subnetMask}")
                    print(f"MTU is {vnic.spec.mtu}")
                    print("\n")
    else:
        print("No virtual network adapters found")


# Main section
if __name__ == "__main__":
    sys.exit(main())
