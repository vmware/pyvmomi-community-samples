#!/usr/bin/env python
"""
Written by Chris Hupman
Github: https://github.com/chupman/
Get guest info with parent folder, cluster, and host information.
Also has parameter options for csv and json export
"""
from __future__ import print_function

from pyVmomi import vim

from pyVim.connect import SmartConnect, Disconnect

import argparse
import atexit
import getpass
import csv
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
    parser.add_argument('--csv', required=False, action='store_true',
                        help='Write output to csv file')
    parser.add_argument('--csvfile', required=False, action='store',
                        default='getvmsbycluster.csv',
                        help='Filename and path of csv file')
    parser.add_argument('--json', required=False, action='store_true',
                        help='Write out to json file')
    parser.add_argument('--jsonfile', required=False, action='store',
                        default='getvmsbycluster.json',
                        help='Filename and path of json file')
    parser.add_argument('--silent', required=False, action='store_true',
                        help='supress output to screen')
    args = parser.parse_args()
    return args


def vmsummary(summary):
    vmsum = {}
    config = summary.config
    ipaddr = summary.guest.ipAddress
    vmsum['mem'] = str(config.memorySizeMB / 1024)
    vmsum['disk'] = str(summary.storage.committed / 1073741824)
    vmsum['cpu'] = str(config.numCpu)
    vmsum['path'] = config.vmPathName
    vmsum['guestname'] = config.guestFullName
    vmsum['state'] = summary.runtime.powerState
    vmsum['managedby'] = config.managedBy if config.managedBy else ''
    vmsum['annotation'] = config.annotation if config.annotation else ''
    vmsum['ip'] = ipaddr if ipaddr is not None else ''

    return vmsum


def vmprint(dc, cluster, host, vm, summary):
    print("VM: " + vm.summary.config.name + " Host: " + host, end="")
    print(" Folder: " + vm.parent.name + " Cluster: " + cluster, end="")
    print("    IP: " + summary['ip'] + " CPU: " + summary['cpu'], end="")
    print(" Mem: " + summary['mem'] + " Disk: " + summary['disk'])
    print("    State: " + summary['state'], end=""),
    print(" Managedby: " + summary['managedby'], end=""),
    print(" Path: " + summary['path'])
    if summary['annotation'] is not '':
        print("    Annotation: " + summary['annotation'])


def vm2dict(dc, cluster, host, vm, summary):
    # If nested folder path is required, split into a separate function
    vmname = vm.summary.config.name
    data[dc][cluster][host][vmname]['folder'] = vm.parent.name
    data[dc][cluster][host][vmname]['mem'] = summary['mem']
    data[dc][cluster][host][vmname]['disk'] = summary['disk']
    data[dc][cluster][host][vmname]['cpu'] = summary['cpu']
    data[dc][cluster][host][vmname]['path'] = summary['path']
    data[dc][cluster][host][vmname]['ip'] = summary['ip']
    data[dc][cluster][host][vmname]['guestname'] = summary['guestname']
    data[dc][cluster][host][vmname]['state'] = summary['state']
    data[dc][cluster][host][vmname]['managedby'] = summary['managedby']
    data[dc][cluster][host][vmname]['annotation'] = summary['annotation']


def data2csv(data, args):
    with open(args.csvfile, 'w') as csvfile:
        fieldnames = ['datacenter', 'cluster', 'host', 'folder', 'vmname',
                      'disk', 'cpu', 'mem', 'path', 'guestname', 'state',
                      'managedby', 'annotation', 'ip']
        writer = csv.writer(csvfile)
        writer.writerow(fieldnames)
        for dc, clusters in data.iteritems():
            for cl, hosts in clusters.iteritems():
                for host, vms in hosts.iteritems():
                    for vm in vms:
                        currvm = data[dc][cl][host][vm]
                        vmdata = [dc, cl, host, currvm['folder'], vm,
                                  currvm['disk'], currvm['cpu'], currvm['mem'],
                                  currvm['path'], currvm['guestname'],
                                  currvm['state'], currvm['managedby'],
                                  currvm['annotation'], currvm['ip']]
                        writer.writerow(vmdata)


def data2json(data, args):
    with open(args.jsonfile, 'w') as f:
        json.dump(data, f)


def main():
    """
    Iterate through all datacenters and list VM info.
    """
    args = GetArgs()
    json = True if args.json else False
    csv = True if args.csv else False

    if args.password:
        password = args.password
    else:
        password = getpass.getpass(prompt='Enter password for host %s and '
                                   'user %s: ' % (args.host, args.user))

    si = SmartConnect(host=args.host,
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
        if hasattr(child, 'hostFolder'):
            dc = child
            data[dc.name] = {}  # Add data Centers to data dict
            clusters = dc.hostFolder.childEntity
            for cluster in clusters:  # Iterate through the clusters in the DC
                # Add Clusters to data dict
                data[dc.name][cluster.name] = {}
                hosts = cluster.host
                for host in hosts:  # Iterate through Hosts in the Cluster
                    hostname = host.summary.config.name
                    # Add VMs to data dict by config name
                    data[dc.name][cluster.name][hostname] = {}
                    vms = host.vm
                    for vm in vms:  # Iterate through each VM on the host
                        vmname = vm.summary.config.name
                        data[dc.name][cluster.name][hostname][vmname] = {}
                        summary = vmsummary(vm.summary)  # get vmguest info
                        vm2dict(dc.name, cluster.name, hostname, vm, summary)
                        if not args.silent:
                            vmprint(dc.name, cluster.name,
                                    hostname, vm, summary)
        else:
            # some other non-datacenter type object
            continue

    if json:
        data2json(data, args)
    if csv:
        data2csv(data, args)

# Start program
if __name__ == "__main__":
    main()
