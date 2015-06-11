#!/usr/bin/env python
"""
vSphere Python SDK program for listing all ESXi datastores and their
associated devices
"""
import argparse
import atexit

from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim

from tools import cli


def get_args():
    parser = argparse.ArgumentParser(
        description='Process args for retrieving all the Virtual Machines')
    parser.add_argument('-s', '--host', required=True, action='store',
                        help='Remote host to connect to')
    parser.add_argument('-o', '--port', type=int, default=443, action='store',
                        help='Port to connect on')
    parser.add_argument('-u', '--user', required=True, action='store',
                        help='User name to use when connecting to host')
    parser.add_argument('-p', '--password', required=True, action='store',
                        help='Password to use when connecting to host')
    args = parser.parse_args()
    return args


def main():
    """
   Simple command-line program for listing all ESXi datastores and their
   associated devices
   """

    args = get_args()
    cli.prompt_for_password(args)

    try:
        service_instance = connect.SmartConnect(host=args.host,
                                                user=args.user,
                                                pwd=args.password,
                                                port=int(args.port))
        if not service_instance:
            print("Could not connect to the specified host using specified "
                  "username and password")
            return -1

        atexit.register(connect.Disconnect, service_instance)

        content = service_instance.RetrieveContent()
        # Search for all ESXi hosts
        objview = content.viewManager.CreateContainerView(content.rootFolder,
                                                          [vim.HostSystem],
                                                          True)
        esxi_hosts = objview.view
        objview.Destroy()

        for esxi_host in esxi_hosts:
            print("Shutting down host %s" % esxi_host.name)
            vim.HostSystem.Shutdown(esxi_host, True)

    except vmodl.MethodFault as error:
        print "Caught vmodl fault : " + error.msg
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
