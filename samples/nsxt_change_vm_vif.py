#!/usr/bin/env python
"""
Written by Yasen Simeonov
Github: https://github.com/yasensim

This code is released under the terms of the Apache 2
http://www.apache.org/licenses/LICENSE-2.0.html

Example script to change the network of the Virtual Machine NIC
that includes NSX-T opeque switch

"""

import atexit
from tools import tasks, pchelper, cli, service_instance
from pyVim import connect
from pyVmomi import vim, vmodl


def main():
    """
    Simple command-line program for changing network virtual machines NIC
    that includes NSX-T opeque switch.
    """

    parser = cli.Parser()
    # --port-group : 'Name of the portgroup or NSX-T Logical Switch'
    parser.add_required_arguments(cli.Argument.VM_NAME, cli.Argument.PORT_GROUP)
    args = parser.get_args()
    serviceInstance = service_instance.connect(args)

    try:
        atexit.register(connect.Disconnect, serviceInstance)
        content = serviceInstance.RetrieveContent()
        vm = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)
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

                # NSX-T Logical Switch
                if isinstance(pchelper.get_obj(content,
                                      [vim.Network],
                                      args.port_group), vim.OpaqueNetwork):
                    network = \
                        pchelper.get_obj(content, [vim.Network], args.port_group)
                    nicspec.device.backing = \
                        vim.vm.device.VirtualEthernetCard. \
                        OpaqueNetworkBackingInfo()
                    network_id = network.summary.opaqueNetworkId
                    network_type = network.summary.opaqueNetworkType
                    nicspec.device.backing.opaqueNetworkType = network_type
                    nicspec.device.backing.opaqueNetworkId = network_id

                # vSphere Distributed Virtual Switch
                elif hasattr(pchelper.get_obj(content,
                                     [vim.Network],
                                     args.port_group), 'portKeys'):
                    network = pchelper.get_obj(content,
                                      [vim.dvs.DistributedVirtualPortgroup],
                                      args.port_group)
                    dvs_port_connection = vim.dvs.PortConnection()
                    dvs_port_connection.portgroupKey = network.key
                    dvs_port_connection.switchUuid = \
                        network.config.distributedVirtualSwitch.uuid
                    nicspec.device.backing = \
                        vim.vm.device.VirtualEthernetCard. \
                        DistributedVirtualPortBackingInfo()
                    nicspec.device.backing.port = dvs_port_connection

                # vSphere Standard Switch
                else:
                    nicspec.device.backing = \
                        vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                    nicspec.device.backing.network = \
                        pchelper.get_obj(content, [vim.Network], args.port_group)
                    nicspec.device.backing.deviceName = args.port_group

                nicspec.device.connectable = \
                    vim.vm.device.VirtualDevice.ConnectInfo()
                nicspec.device.connectable.startConnected = True
                nicspec.device.connectable.allowGuestControl = True
                nicspec.device.connectable.connected = True
                device_change.append(nicspec)
                break

        config_spec = vim.vm.ConfigSpec(deviceChange=device_change)
        task = vm.ReconfigVM_Task(config_spec)
        tasks.wait_for_tasks(serviceInstance, [task])
        print("Successfully changed network")

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
