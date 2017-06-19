#!/usr/bin/env python

import atexit
import argparse
import getpass
import ssl

from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect

"""
Example of connecting to the ESXTOP service provided
by vCenter Server's Service Manager
"""

__author__ = 'William Lam'


def GetArgs():
    """
    Supports the command-line arguments listed below.
    """
    parser = argparse.ArgumentParser(
        description='ESXTOP metric collection via vCenter Server')
    parser.add_argument('-s', '--host', required=True, action='store',
                        help='Remote host to connect to')
    parser.add_argument('-o', '--port', type=int, default=443, action='store',
                        help='Port to connect on')
    parser.add_argument('-u', '--user', required=True, action='store',
                        help='User name to use when connecting to host')
    parser.add_argument('-p', '--password', required=False, action='store',
                        help='Password to use when connecting to host')
    parser.add_argument('-e', '--esxi', required=False, action='store',
                        help='ESXi hostname/IP managed by vCenter Server')
    args = parser.parse_args()
    return args


# Start program
def main():
    args = GetArgs()
    if args.password:
        password = args.password
    else:
        password = getpass.getpass(
            prompt='Enter password for host %s and '
                   'user %s: ' % (args.host, args.user))

    context = None
    if hasattr(ssl, "_create_unverified_context"):
        context = ssl._create_unverified_context()
    si = SmartConnect(host=args.host,
                      user=args.user,
                      pwd=password,
                      port=int(args.port),
                      sslContext=context)

    atexit.register(Disconnect, si)

    # "vmware.host." prefix is required when connecting to VC
    location = "vmware.host." + args.esxi

    services = si.content.serviceManager.QueryServiceList(
        location=[location])

    if services:
        for service in services:
            if service.serviceName == "Esxtop":
                results = service.service.ExecuteSimpleCommand(
                    arguments=["CounterInfo"])
                print(results)
    else:
        print("Unable to retrieve the service list from \
ESXi host. Pleaes ensure --esxi property is the FQDN or IP \
Address of the managed ESXi host in your vCenter Server")


# Start program
if __name__ == "__main__":
    main()
