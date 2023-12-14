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

def stop_ssh_service(host):
    service_system = host.configManager.serviceSystem
    services = service_system.serviceInfo.service

    for service in services:
        if service.key == "TSM-SSH":
            if service.running:
                print(f"Stopping SSH service on {host.name}")
                service_system.StopService(service.key)
                print("SSH service stopped successfully.")
            else:
                print(f"SSH service is already stopped on {host.name}")
            return

    print("SSH service not found on the host.")

def main():
    parser = cli.Parser()
    args = parser.get_args()
    si = service_instance.connect(args)
    content = si.RetrieveContent()

    hosts = get_vm_hosts(content)

    if hosts:
        for host in hosts:
            stop_ssh_service(host)

if __name__ == "__main__":
    sys.exit(main())

