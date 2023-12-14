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


def reboot_hosts(hosts):
    for host in hosts:
        try:
            print(f"Rebooting host {host.name}...")
            task = host.RebootHost_Task(force=True)
            return task.info
        except Exception as e:
            print(f"Error rebooting host: {e}")

def main():
    parser = cli.Parser()
    args = parser.get_args()
    si = service_instance.connect(args)
    content = si.RetrieveContent()

    hosts = get_vm_hosts(content)

    task_info = reboot_hosts(hosts)
    if task_info:
        print("Task was executed successfully")
    else:
        print("Error rebooting host")

# Main section
if __name__ == "__main__":
    sys.exit(main())
