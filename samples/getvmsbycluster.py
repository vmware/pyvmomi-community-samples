#!/usr/bin/env python
"""
Written by Chris Hupman
Github: https://github.com/chupman/
Example: Get guest info with folder and host placement

"""
from __future__ import print_function
from tools import cli, service_instance
import argparse
import json


data = {}


def get_nics(guest):
    nics = {}
    for nic in guest.net:
        if nic.network:  # Only return adapter backed interfaces
            if nic.ipConfig is not None and nic.ipConfig.ipAddress is not None:
                nics[nic.macAddress] = {}  # Use mac as uniq ID for nic
                nics[nic.macAddress]['netlabel'] = nic.network
                ipconf = nic.ipConfig.ipAddress
                i = 0
                nics[nic.macAddress]['ipv4'] = {}
                for ip in ipconf:
                    if ":" not in ip.ipAddress:  # Only grab ipv4 addresses
                        nics[nic.macAddress]['ipv4'][i] = ip.ipAddress
                        nics[nic.macAddress]['prefix'] = ip.prefixLength
                        nics[nic.macAddress]['connected'] = nic.connected
                    i = i+1
    return nics


def vmsummary(summary, guest):
    vmsum = {}
    config = summary.config
    net = get_nics(guest)
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


def data2json(raw_data, args):
    with open(args.jsonfile, 'w') as f:
        json.dump(raw_data, f)


def main():
    """
    Iterate through all datacenters and list VM info.
    """
    parser = cli.Parser()
    parser.add_custom_argument('--json', required=False, action='store_true',
                               help='Write out to json file')
    parser.add_custom_argument('--jsonfile', required=False, action='store', default='getvmsbycluster.json',
                               help='Filename and path of json file')
    parser.add_custom_argument('--silent', required=False, action='store_true',
                               help='supress output to screen')
    args = parser.get_args()
    si = service_instance.connect(args)
    outputjson = True if args.json else False

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
