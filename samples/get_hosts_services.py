#!/usr/bin/env python

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

def get_host_services_status(host):
    service_system = host.configManager.serviceSystem
    services_info = service_system.serviceInfo.service

    services_status = {}
    for service in services_info:
        services_status[service.key] = {
            'name': service.label,
            'running': service.running,
        }

    return services_status

def main():
    parser = cli.Parser()
    args = parser.get_args()
    si = service_instance.connect(args)
    content = si.RetrieveContent()

    hosts = get_vm_hosts(content)
    
    if hosts:
        print("Service Status on Hosts:\n")
        for host in hosts:
            services_status = get_host_services_status(host)
            print(f"Host: {host.name}")
            
            for service_key, service_info in services_status.items():
                print(f"Service: {service_info['name']}")
                print(f"Status: {'Running' if service_info['running'] else 'Not Running'}")
                print()

if __name__ == "__main__":
    sys.exit(main())


