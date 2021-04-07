#!/usr/bin/env python
"""
Python program for flat text listing the VMs on an
ESX / vCenter, host one per line.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from __future__ import print_function
from tools import cli, service_instance

MAX_DEPTH = 10


def print_vminfo(vm, depth=1):
    """
    Print information for a particular virtual machine or recurse into a folder
    with depth protection
    """

    # if this is a group it will have children. if it does, recurse into them
    # and then return
    if hasattr(vm, 'childEntity'):
        if depth > MAX_DEPTH:
            return
        vmlist = vm.childEntity
        for child in vmlist:
            print_vminfo(child, depth+1)
        return

    summary = vm.summary
    print(summary.config.name)


def main():
    """
    Simple command-line program for listing the virtual machines on a host.
    """

    parser = cli.Parser()
    args = parser.get_args()
    si = service_instance.connect(args)

    content = si.RetrieveContent()
    for child in content.rootFolder.childEntity:
        if hasattr(child, 'vmFolder'):
            datacenter = child
            vmfolder = datacenter.vmFolder
            vmlist = vmfolder.childEntity
            for vm in vmlist:
                print_vminfo(vm)


# Start program
if __name__ == "__main__":
    main()
