#!/usr/bin/env python
"""
Written by Reubenur Rahman
Github: https://github.com/rreubenur/

This code is released under the terms of the Apache 2
http://www.apache.org/licenses/LICENSE-2.0.html

Example script to change the network of the Virtual Machine NIC

"""

import atexit

from tools import cli, tasks, service_instance, pchelper
from pyVmomi import vim, vmodl


def main():
    """
    Simple command-line program for changing network virtual machines NIC.
    """

    parser = cli.Parser()
    parser.add_optional_arguments(cli.Argument.UUID, cli.Argument.VM_NAME, cli.Argument.NETWORK_NAME)
    parser.add_custom_argument('--is_VDS',
                               action="store_true",
                               default=False,
                               help='The provided network is in VSS or VDS')
    args = parser.get_args()
    si = service_instance.connect(args)

    try:
        content = si.RetrieveContent()
        vm = None
        if args.uuid:
            vm = content.searchIndex.FindByUuid(None, args.uuid, True)
        elif args.vm_name:
            vm = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)

        if not vm:
            raise SystemExit("Unable to locate VirtualMachine.")

        # This code is for changing only one Interface. For multiple Interface
        # Iterate through a loop of network names.
        device_change = []
        for device in vm.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualEthernetCard):
                nicspec = vim.vm.device.VirtualDeviceSpec()
                nicspec.operation = \
                    vim.vm.device.VirtualDeviceSpec.Operation.edit
                nicspec.device = device
                nicspec.device.wakeOnLanEnabled = True

                if not args.is_VDS:
                    nicspec.device.backing = \
                        vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                    nicspec.device.backing.network = \
                        pchelper.get_obj(content, [vim.Network], args.network_name)
                    nicspec.device.backing.deviceName = args.network_name
                else:
                    network = pchelper.get_obj(content, [vim.dvs.DistributedVirtualPortgroup], args.network_name)
                    dvs_port_connection = vim.dvs.PortConnection()
                    dvs_port_connection.portgroupKey = network.key
                    dvs_port_connection.switchUuid = \
                        network.config.distributedVirtualSwitch.uuid
                    nicspec.device.backing = \
                        vim.vm.device.VirtualEthernetCard. \
                        DistributedVirtualPortBackingInfo()
                    nicspec.device.backing.port = dvs_port_connection

                nicspec.device.connectable = \
                    vim.vm.device.VirtualDevice.ConnectInfo()
                nicspec.device.connectable.startConnected = True
                nicspec.device.connectable.allowGuestControl = True
                device_change.append(nicspec)
                break

        config_spec = vim.vm.ConfigSpec(deviceChange=device_change)
        task = vm.ReconfigVM_Task(config_spec)
        tasks.wait_for_tasks(si, [task])
        print("Successfully changed network")

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
