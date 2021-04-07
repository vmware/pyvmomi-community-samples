#!/usr/bin/env python
#
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
Python program for powering on VMs
"""

from pyVmomi import vim, vmodl
from tools import cli, service_instance
from tools.tasks import wait_for_tasks


def main():
    """
    Simple command-line program for powering on virtual machines on a system.
    """

    parser = cli.Parser()
    parser.add_custom_argument('-v', '--vm-name', required=True, action='append',
                               help='Names of the Virtual Machines to power on')
    args = parser.get_args()
    # form a connection...
    si = service_instance.connect(args)

    try:
        vmnames = args.vm_name
        if not len(vmnames):
            print("No virtual machine specified for poweron")

        # Retreive the list of Virtual Machines from the inventory objects
        # under the rootFolder
        content = si.content
        obj_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
        vm_list = obj_view.view
        obj_view.Destroy()

        # Find the vm and power it on
        tasks = [vm.PowerOn() for vm in vm_list if vm.name in vmnames]

        # Wait for power on to complete
        wait_for_tasks(si, tasks)

        print("Virtual Machine(s) have been powered on successfully")
    except vmodl.MethodFault as e:
        print("Caught vmodl fault : " + e.msg)
    except Exception as e:
        print("Caught Exception : " + str(e))


# Start program
if __name__ == "__main__":
    main()
