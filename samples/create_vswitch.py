"""
Written by Reubenur Rahman
Github: https://github.com/rreubenur/

This code is released under the terms of the Apache 2
http://www.apache.org/licenses/LICENSE-2.0.html

Example script to create a Vsphere Standard Switch

"""

import atexit
import getpass

from tools import cli
from pyVim import connect
from pyVmomi import vim, vmodl


def get_args():
    """Get command line args from the user.
    """
    parser = cli.build_arg_parser()

    parser.add_argument('-e', '--esx_host',
                        required=True,
                        help='Name/IP of the Physical Host on which '
                             'you want to add the vSwitch')

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
    """
    Creates a Vsphere Standard Switch on the specified host
    """
    vss_spec = vim.host.VirtualSwitch.Specification()
    vss_spec.numPorts = num_ports

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
        #content = service_instance.RetrieveContent()

        if not service_instance:
            raise SystemExit("Unable to connect to host with supplied info.")

        host = service_instance.content.searchIndex. \
            FindByIp(None, args.esx_host, False)

        if not host:
            raise SystemExit("Unable to locate Physical Host.")

        host_network_system = host.configManager.networkSystem

        create_vswitch(host_network_system, args.vswitch_name,
                       int(args.num_port), args.pnic_name)

    except vmodl.MethodFault as error:
        print "Caught vmodl fault : " + error.msg
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
