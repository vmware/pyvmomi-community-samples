#!/usr/bin/env python
"""
Written by Chris Hupman
Github: https://github.com/chupman/
Example: Get guest info with folder and host placement

"""
from __future__ import print_function

from pyVmomi import vim

from pyVim.connect import SmartConnectNoSSL, Disconnect

import argparse
import atexit
import getpass
import json


data = {}


def GetArgs():
    """
    Supports the command-line arguments listed below.
    """
    parser = argparse.ArgumentParser(
        description='Process args for retrieving all the Virtual Machines')
    parser.add_argument('-s', '--host', required=True, action='store',
                        help='Remote host to connect to')
    parser.add_argument('-o', '--port', type=int, default=443, action='store',
                        help='Port to connect on')
    parser.add_argument('-u', '--user', required=True, action='store',
                        help='User name to use when connecting to host')
    parser.add_argument('-p', '--password', required=False, action='store',
                        help='Password to use when connecting to host')
    parser.add_argument('--json', required=False, action='store_true',
                        help='Write out to json file')
    parser.add_argument('--jsonfile', required=False, action='store',
                        default='getvmsbycluster.json',
                        help='Filename and path of json file')
    parser.add_argument('--silent', required=False, action='store_true',
                        help='supress output to screen')
    args = parser.parse_args()
    return args


def getNICs(summary, guest):
    nics = {}
    for nic in guest.net:
        if nic.network:  # Only return adapter backed interfaces
            if nic.ipConfig is not None and nic.ipConfig.ipAddress is not None:
                nics[nic.macAddress] = {}  # Use mac as uniq ID for nic
                nics[nic.macAddress]['netlabel'] = nic.network
                ipconf = nic.ipConfig.ipAddress
                for ip in ipconf:
                    if ":" not in ip.ipAddress:  # Only grab ipv4 addresses
                        nics[nic.macAddress]['ip'] = ip.ipAddress
                        nics[nic.macAddress]['prefix'] = ip.prefixLength
                        nics[nic.macAddress]['connected'] = nic.connected
    return nics


def vmsummary(summary, guest):
    vmsum = {}
    config = summary.config
    net = getNICs(summary, guest)
    vmsum['mem'] = str(config.memorySizeMB / 1024)
    vmsum['diskGB'] = str("%.2f" % (summary.storage.committed / 1024**3))
    vmsum['cpu'] = str(config.numCpu)
    vmsum['path'] = config.vmPathName
    vmsum['ostype'] = config.guestFullName
    vmsum['state'] = summary.runtime.powerState
    vmsum['annotation'] = config.annotation if config.annotation else ''
    vmsum['net'] = net

    return vmsum


def vm2dict(dc, cluster, host, vm, summary):
    # If nested folder path is required, split into a separate function
    vmname = vm.summary.config.name
    data[dc][cluster][host][vmname]['folder'] = vm.parent.name
    data[dc][cluster][host][vmname]['mem'] = summary['mem']
    data[dc][cluster][host][vmname]['diskGB'] = summary['diskGB']
    data[dc][cluster][host][vmname]['cpu'] = summary['cpu']
    data[dc][cluster][host][vmname]['path'] = summary['path']
    data[dc][cluster][host][vmname]['net'] = summary['net']
    data[dc][cluster][host][vmname]['ostype'] = summary['ostype']
    data[dc][cluster][host][vmname]['state'] = summary['state']
    data[dc][cluster][host][vmname]['annotation'] = summary['annotation']


def data2json(data, args):
    with open(args.jsonfile, 'w') as f:
        json.dump(data, f)


def main():
    """
    Iterate through all datacenters and list VM info.
    """
    args = GetArgs()
    outputjson = True if args.json else False

    if args.password:
        password = args.password
    else:
        password = getpass.getpass(prompt='Enter password for host %s and '
                                   'user %s: ' % (args.host, args.user))

    si = SmartConnectNoSSL(host=args.host,
                           user=args.user,
                           pwd=password,
                           port=int(args.port))
    if not si:
        print("Could not connect to the specified host using specified "
              "username and password")
        return -1

    atexit.register(Disconnect, si)

    content = si.RetrieveContent()
    children = content.rootFolder.childEntity
    for child in children:  # Iterate though DataCenters
        dc = child
        data[dc.name] = {}  # Add data Centers to data dict
        clusters = dc.hostFolder.childEntity
        for cluster in clusters:  # Iterate through the clusters in the DC
            # Add Clusters to data dict
            data[dc.name][cluster.name] = {}
            hosts = cluster.host  # Variable to make pep8 compliance
            for host in hosts:  # Iterate through Hosts in the Cluster
                hostname = host.summary.config.name
                # Add VMs to data dict by config name
                data[dc.name][cluster.name][hostname] = {}
                vms = host.vm
                for vm in vms:  # Iterate through each VM on the host
                    vmname = vm.summary.config.name
                    data[dc.name][cluster.name][hostname][vmname] = {}
                    summary = vmsummary(vm.summary, vm.guest)
                    vm2dict(dc.name, cluster.name, hostname, vm, summary)

    if not args.silent:
        print(json.dumps(data, sort_keys=True, indent=4))

    if outputjson:
        data2json(data, args)

# Start program
if __name__ == "__main__":
    main()
