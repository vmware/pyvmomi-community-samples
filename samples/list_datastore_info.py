#!/usr/bin/env python
# William Lam
# www.virtuallyghetto.com

"""
vSphere Python SDK program for listing all ESXi datastores and their
associated devices
"""
import argparse
import atexit
import json

from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim

from tools import cli


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
    parser.add_argument('-p', '--password', required=True, action='store',
                        help='Password to use when connecting to host')
    parser.add_argument('-j', '--json', default=False, action='store_true',
                        help='Output to JSON')
    args = parser.parse_args()
    return args


# http://stackoverflow.com/questions/1094841/
def sizeof_fmt(num):
    for x in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')


def print_fs(fs):
    print "{}\t{}\t".format("Datastore:     ", fs.volume.name)
    print "{}\t{}\t".format("UUID:          ", fs.volume.uuid)
    print "{}\t{}\t".format("Capacity:      ", sizeof_fmt(fs.volume.capacity))
    print "{}\t{}\t".format("VMFS Version:  ", fs.volume.version)
    print "{}\t{}\t".format("Is Local VMFS: ", fs.volume.local)
    print "{}\t{}\t".format("SSD:           ", fs.volume.ssd)


def main():
    """
   Simple command-line program for listing all ESXi datastores and their
   associated devices
   """

    args = GetArgs()

    cli.prompt_for_password(args)

    try:
        si = None
        try:
            si = connect.SmartConnect(host=args.host,
                                      user=args.user,
                                      pwd=args.password,
                                      port=int(args.port))
        except IOError, e:
            pass
        if not si:
            print("Could not connect to the specified host using specified "
                  "username and password")
            return -1

        atexit.register(connect.Disconnect, si)

        content = si.RetrieveContent()
        # Search for all ESXi hosts
        objView = content.viewManager.CreateContainerView(content.rootFolder,
                                                          [vim.HostSystem],
                                                          True)
        esxi_hosts = objView.view
        objView.Destroy()

        datastores = {}
        for esxi_host in esxi_hosts:
            if not args.json:
                print "{}\t{}\t\n".format("ESXi Host:    ", esxi_host.name)

            # All Filesystems on ESXi host
            storage_system = esxi_host.configManager.storageSystem
            fss = storage_system.fileSystemVolumeInfo.mountInfo

            datastore_dict = {}
            # Map all filesystems
            for fs in fss:
                # Extract only VMFS volumes
                if fs.volume.type == "VMFS":

                    extents = fs.volume.extent
                    if not args.json:
                        print_fs(fs)
                    else:
                        datastore_details = {'uuid': fs.volume.uuid,
                                             'capacity': fs.volume.capacity,
                                             'vmfs_version': fs.volume.version,
                                             'local': fs.volume.local,
                                             'ssd': fs.volume.ssd}

                    extent_arr = []
                    extent_count = 0
                    for extent in extents:
                        if not args.json:
                            print "{}\t{}\t".format(
                                "Extent[" + str(extent_count) + "]:",
                                extent.diskName)
                            extent_count += 1
                        else:
                            # create an array of the devices backing the given
                            # datastore
                            extent_arr.append(extent.diskName)
                            # add the extent array to the datastore info
                            datastore_details['extents'] = extent_arr
                            # associate datastore details with datastore name
                            datastore_dict[fs.volume.name] = datastore_details
                    if not args.json:
                        print

            # associate ESXi host with the datastore it sees
            datastores[esxi_host.name] = datastore_dict

        if args.json:
            print json.dumps(datastores)

    except vmodl.MethodFault, e:
        print "Caught vmodl fault : " + e.msg
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
