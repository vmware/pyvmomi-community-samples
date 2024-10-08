#!/usr/bin/env python
"""
Written by Chris Hupman
Github: https://github.com/chupman/
Example: Get guest info with folder and host placement

"""
import json, csv
from tools import cli, service_instance


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


def vm2dict(datacenter, cluster, host, vm, summary):
    # If nested folder path is required, split into a separate function
    vmname = vm.summary.config.name
    data[datacenter][cluster][host][vmname]['folder'] = vm.parent.name
    data[datacenter][cluster][host][vmname]['mem'] = summary['mem']
    data[datacenter][cluster][host][vmname]['diskGB'] = summary['diskGB']
    data[datacenter][cluster][host][vmname]['cpu'] = summary['cpu']
    data[datacenter][cluster][host][vmname]['path'] = summary['path']
    data[datacenter][cluster][host][vmname]['net'] = summary['net']
    data[datacenter][cluster][host][vmname]['ostype'] = summary['ostype']
    data[datacenter][cluster][host][vmname]['state'] = summary['state']
    data[datacenter][cluster][host][vmname]['annotation'] = summary['annotation']


def data2json(raw_data, args):
    with open(args.jsonfile, 'w') as json_file:
        json.dump(raw_data, json_file)

def data2csv(data,args):
    with open(args.csvfile, 'w') as csv_file:
        csv_columns = ['datacenter','cluster','folder','host','vmname','mem','diskGB','cpu','mac_address','ipv4','ostype','state','annotation']
        writer = csv.DictWriter(csv_file, fieldnames=csv_columns)
        writer.writeheader()

        for datacenter in data:
            for cluster in data[datacenter]:
                for host in data[datacenter][cluster]:
                    for vmname in data[datacenter][cluster][host]:
                        vm_row = dict()
                        vm_row['datacenter'] = datacenter
                        vm_row['cluster'] = cluster
                        vm_row['folder'] = data[datacenter][cluster][host][vmname]['folder']
                        vm_row['host'] = host
                        vm_row['vmname'] = vmname
                        vm_row['mem'] = data[datacenter][cluster][host][vmname]['mem']
                        vm_row['diskGB'] = data[datacenter][cluster][host][vmname]['diskGB']
                        vm_row['cpu'] = data[datacenter][cluster][host][vmname]['cpu']
                        vm_row['mac_address'] = ''
                        vm_row['ipv4'] = ''
                        for nc in data[datacenter][cluster][host][vmname]['net']:
                            vm_row['mac_address'] += ';' + nc
                            for ipv4 in data[datacenter][cluster][host][vmname]['net'][nc]['ipv4']:
                                vm_row['ipv4'] += ';' + data[datacenter][cluster][host][vmname]['net'][nc]['ipv4'][ipv4]
                        
                        vm_row['ostype']= data[datacenter][cluster][host][vmname]['ostype']
                        vm_row['state'] = data[datacenter][cluster][host][vmname]['state']
                        vm_row['annotation'] = data[datacenter][cluster][host][vmname]['annotation']

                        writer.writerow(vm_row)

def main():
    """
    Iterate through all datacenters and list VM info.
    """
    parser = cli.Parser()
    parser.add_custom_argument('--json', required=False, action='store_true',
                               help='Write out to json file')
    parser.add_custom_argument('--jsonfile', required=False, action='store',
                               default='getvmsbycluster.json',
                               help='Filename and path of json file')
    parser.add_custom_argument('--csv', required=False, action='store_true',
                               help='Write out to csv file')
    parser.add_custom_argument('--csvfile', required=False, action='store',
                               default='getvmsbycluster.csv',
                               help='Filename and path of csv file')
    parser.add_custom_argument('--silent', required=False, action='store_true',
                               help='supress output to screen')
    args = parser.get_args()
    si = service_instance.connect(args)
    outputjson = True if args.json else False
    outputcsv = True if args.csv else False

    content = si.RetrieveContent()
    children = content.rootFolder.childEntity
    for child in children:  # Iterate though DataCenters
        datacenter = child
        data[datacenter.name] = {}  # Add data Centers to data dict
        clusters = datacenter.hostFolder.childEntity
        for cluster in clusters:  # Iterate through the clusters in the DC
            # Add Clusters to data dict
            data[datacenter.name][cluster.name] = {}
            hosts = cluster.host  # Variable to make pep8 compliance
            for host in hosts:  # Iterate through Hosts in the Cluster
                hostname = host.summary.config.name
                # Add VMs to data dict by config name
                data[datacenter.name][cluster.name][hostname] = {}
                vms = host.vm
                for vm in vms:  # Iterate through each VM on the host
                    vmname = vm.summary.config.name
                    data[datacenter.name][cluster.name][hostname][vmname] = {}
                    summary = vmsummary(vm.summary, vm.guest)
                    vm2dict(datacenter.name, cluster.name, hostname, vm, summary)

    if not args.silent:
        print(json.dumps(data, sort_keys=True, indent=4))

    if outputjson:
        data2json(data, args)

    if outputcsv:
        data2csv(data, args)

# Start program
if __name__ == "__main__":
    main()

