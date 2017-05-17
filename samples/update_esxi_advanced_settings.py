#!/usr/bin/env python
# William Lam
# www.virtuallyghetto.com

"""
vSphere Python SDK program for updating ESXi Advanced Settings

Usage:
    python update_esxi_advanced_settings.py -s 192.168.1.200 \
    -u 'administrator@vsphere.local' \
    -p VMware1! -c VSAN-Cluster -k VSAN.ClomRepairDelay -v 120
"""

import argparse
import atexit
import getpass
import ssl

from pyVmomi import vim, vmodl
from pyVim import connect
from pyVim.connect import SmartConnectNoSSL


def get_args():
    parser = argparse.ArgumentParser(
        description='Process args for setting ESXi advanced settings')

    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='Remote host to connect to')

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

    parser.add_argument('-c', '--cluster_name',
                        required=True,
                        action='store',
                        help='Name of vSphere Cluster to update ESXi \
                             Advanced Setting')
    parser.add_argument('-k', '--key',
                        required=True,
                        action='store',
                        help='Name of ESXi Advanced Setting to update')
    parser.add_argument('-v', '--value',
                        required=True,
                        action='store',
                        help='Value of the ESXi Advanced Setting to update')

    args = parser.parse_args()
    if not args.password:
        args. password = getpass.getpass(
            prompt='Enter password for host %s and user %s: ' %
                   (args.host, args.user))

    return args


def get_obj(content, vimtype, name):
    """
    Return an object by name, if name is None the
    first found object is returned
    """
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if name:
            if c.name == name:
                obj = c
                break
        else:
            obj = c
            break

    return obj


def main():
    """
   Simple command-line program demonstrating how to update
   ESXi Advanced Settings
   """

    args = get_args()
    try:
        service_instance = connect.SmartConnectNoSSL(host=args.host,
                                                     user=args.user,
                                                     pwd=args.password,
                                                     port=int(args.port))
        if not service_instance:
            print("Could not connect to the specified host using specified "
                  "username and password")
            return -1

        atexit.register(connect.Disconnect, service_instance)

        content = service_instance.RetrieveContent()

        cluster = get_obj(content,
                          [vim.ClusterComputeResource], args.cluster_name)

        hosts = cluster.host
        for host in hosts:
            optionManager = host.configManager.advancedOption
            option = vim.option.OptionValue(key=args.key,
                                            value=long(args.value))
            print("Updating %s on ESXi host %s "
                  "with value of %s" % (args.key, host.name, args.value))
            optionManager.UpdateOptions(changedValue=[option])

    except vmodl.MethodFault as e:
        print("Caught vmodl fault : " + e.msg)
        return -1
    except Exception as e:
        print("Caught exception : " + str(e))
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
