#!/usr/bin/env python
# VMware vSphere Python SDK
# Copyright (c) 2008-2021 VMware, Inc. All Rights Reserved.
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
Python program for finding which VMS have a specific Datastore connected on an ESX / vCenter host
Currently looking for VirtualDrive and VirtualCdrom (can be easilly expanded)
"""

from pyVmomi import vmodl
from pyVmomi import vim
from tools import cli, service_instance, vm

def find_vms_datastore(si, datastore_name):
    # Retrieve the content
    content = si.RetrieveContent()

    # Find the datastore object
    datastore = None
    for datacenter in content.rootFolder.childEntity:
        for ds in datacenter.datastore:
            if ds.name == datastore_name:
                datastore = ds
                break
        if datastore:
            break

    if not datastore:
        print(f"Datastore '{datastore_name}' not found.")
        return -1

    # Find all virtual machines that use this datastore
    vms = []
    for vm in content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], recursive=True).view:
        if (vm.config) == None:
            continue

        for device in vm.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualDisk) or isinstance(device, vim.vm.device.VirtualCdrom):
                if not hasattr(device.backing, "datastore"):
                    continue

                if device.backing.datastore == datastore:
                    vms.append(vm.name)


    # Print out the list of VMs
    if vms:
        print(f"Virtual machines using datastore '{datastore_name}':")
        for vm_name in vms:
            print(f"- {vm_name}")
    else:
        print(f"No virtual machines found using datastore '{datastore_name}'.")


def main():
    """
    Simple command-line program for finding which VMs have a specific Datastore connected.
    CLI arguments
      Required:
        --datastore
      You probably need these:
        -s SERVER_IP_OR_DNS
        -u USER
        --password PASSWORD
    """

    parser = cli.Parser()
    parser.add_custom_argument("--datastore",
                               type=str,
                               action="store",
                               help="Datastore name",
                               required=True)
    
    args = parser.get_args()

    datastore = args.datastore
    if (datastore is None or len(datastore) == 0):
        print("Datastore name is wrong")
        return -1

    try:
        si = service_instance.connect(args)

        # Do work
        exit_code = find_vms_datastore(si, datastore)

    except vmodl.MethodFault as ex:
        print("Caught vmodl fault : {}".format(ex.msg))
        return -1

    return exit_code


# Start program
if __name__ == "__main__":
    main()