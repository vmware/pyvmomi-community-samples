#!/usr/bin/env python
#
# VMware vSphere Python SDK
# Copyright (c) 2021 VMware, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Example for creating a VM
"""

import sys
from pyVmomi import vim
from pyVim.task import WaitForTask
from tools import cli, pchelper, service_instance


def create_vm(si, vm_name, datacenter_name, host_ip, datastore_name=None):

    content = si.RetrieveContent()
    destination_host = pchelper.get_obj(content, [vim.HostSystem], host_ip)
    source_pool = destination_host.parent.resourcePool
    if datastore_name is None:
        datastore_name = destination_host.datastore[0].name

    config = create_config_spec(datastore_name=datastore_name, name=vm_name)
    for child in content.rootFolder.childEntity:
        if child.name == datacenter_name:
            vm_folder = child.vmFolder  # child is a datacenter
            break
    else:
        print("Datacenter %s not found!" % datacenter_name)
        sys.exit(1)

    try:
        WaitForTask(vm_folder.CreateVm(config, pool=source_pool, host=destination_host))
        print("VM created: %s" % vm_name)
    except vim.fault.DuplicateName:
        print("VM duplicate name: %s" % vm_name, file=sys.stderr)
    except vim.fault.AlreadyExists:
        print("VM name %s already exists." % vm_name, file=sys.stderr)


def create_config_spec(datastore_name, name, memory=4, guest="otherGuest",
                       annotation="Sample", cpus=1):
    config = vim.vm.ConfigSpec()
    config.annotation = annotation
    config.memoryMB = int(memory)
    config.guestId = guest
    config.name = name
    config.numCPUs = cpus
    files = vim.vm.FileInfo()
    files.vmPathName = "["+datastore_name+"]"
    config.files = files
    return config


def main():
    parser = cli.Parser()
    parser.add_optional_arguments(cli.Argument.VM_NAME, cli.Argument.DATACENTER_NAME,
                                  cli.Argument.DATASTORE_NAME, cli.Argument.ESX_IP)
    args = parser.get_args()
    si = service_instance.connect(args)
    create_vm(si, args.vm_name, args.datacenter_name, args.esx_ip, args.datastore_name)


# start this thing
if __name__ == "__main__":
    main()
