"""
Written by Reubenur Rahman
Github: https://github.com/rreubenur/

This code is released under the terms of the Apache 2
http://www.apache.org/licenses/LICENSE-2.0.html

Example script to change the network of the Virtual Machine NIC

"""

import atexit
import argparse
import getpass

from tools import tasks
from pyVim import connect
from pyVmomi import vim, vmodl

def get_obj(content, vimtype, name):
    """
     Get the vsphere object associated with a given text name
    """    
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj

def get_args():
    """Get command line args from the user.
    """
    parser = argparse.ArgumentParser(
        description='Standard Arguments for talking to vCenter')
    # because -h is reserved for 'help' we use -s for service
    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='vSphere service to connect to')

    # because we want -p for password, we use -o for port
    parser.add_argument('-o', '--port',
                        type=int,
                        default=443,
                        action='store',
                        help='Port to connect on')

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='User name to use when connecting to host')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to use when connecting to host')
    
    parser.add_argument('-d', '--host_name',
                        required=False,
                        action='store',
                        help='Esxi host name')

    parser.add_argument('-t', '--vswitch_name',
                        required=False,
                        action='store',
                        help='Name of the vSwitch')

    parser.add_argument('-n', '--num_port',
                        required=False,
                        action='store',
                        help='Number of ports')

    parser.add_argument('-i', '--pnic_name',
                        required=False,
                        action='store',
                        help='Physical NIC name (vmnic1/vmnic2)')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password for host %s and user %s: ' %
                   (args.host, args.user))
    return args


def create_vswitch(host_network_system, vss_name, num_ports, nic_name):
    vss_spec = vim.host.VirtualSwitch.Specification()
    vss_spec.numPorts = num_ports
    #vss_spec.bridge = vim.host.VirtualSwitch.SimpleBridge(nicDevice='pnic_key')
    vss_spec.bridge = vim.host.VirtualSwitch.BondBridge(nicDevice=[nic_name])

    host_network_system.AddVirtualSwitch(vswitchName=vss_name, spec=vss_spec)

    print "Successfully created vSwitch ",  vss_name

def main():
    """
    Simple command-line program for changing network virtual machines NIC.
    """

    args = get_args()

    try:
        service_instance = connect.SmartConnect(host=args.host,
                                                user=args.user,
                                                pwd=args.password,
                                                port=int(args.port))

        atexit.register(connect.Disconnect, service_instance)
        content = service_instance.RetrieveContent()

        host = get_obj(content, [vim.HostSystem], args.host_name)

        host_network_system = host.configManager.networkSystem

        create_vswitch(host_network_system, args.vswitch_name, int(args.num_port), args.pnic_name)

    except vmodl.MethodFault as error:
        print "Caught vmodl fault : " + error.msg
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
