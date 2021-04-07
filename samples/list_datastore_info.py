#!/usr/bin/env python
# William Lam
# www.virtuallyghetto.com

"""
vSphere Python SDK program for listing all ESXi datastores and their
associated devices
"""

import json
from pyVmomi import vmodl
from pyVmomi import vim
from tools import cli, service_instance


# http://stackoverflow.com/questions/1094841/
def sizeof_fmt(num):
    """
    Returns the human readable version of a file size

    :param num:
    :return:
    """
    for item in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, item)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')


def print_fs(host_fs):
    """
    Prints the host file system volume info

    :param host_fs:
    :return:
    """
    print("{}\t{}\t".format("Datastore:     ", host_fs.volume.name))
    print("{}\t{}\t".format("UUID:          ", host_fs.volume.uuid))
    print("{}\t{}\t".format("Capacity:      ", sizeof_fmt(
        host_fs.volume.capacity)))
    print("{}\t{}\t".format("VMFS Version:  ", host_fs.volume.version))
    print("{}\t{}\t".format("Is Local VMFS: ", host_fs.volume.local))
    print("{}\t{}\t".format("SSD:           ", host_fs.volume.ssd))


def main():
    """
   Simple command-line program for listing all ESXi datastores and their
   associated devices
   """

    parser = cli.Parser()
    parser.add_custom_argument('--json', default=False, action='store_true', help='Output to JSON')
    args = parser.get_args()
    si = service_instance.connect(args)

    try:

        content = si.RetrieveContent()
        # Search for all ESXi hosts
        objview = content.viewManager.CreateContainerView(content.rootFolder,
                                                          [vim.HostSystem],
                                                          True)
        esxi_hosts = objview.view
        objview.Destroy()

        datastores = {}
        for esxi_host in esxi_hosts:
            if not args.json:
                print("{}\t{}\t\n".format("ESXi Host:    ", esxi_host.name))

            # All Filesystems on ESXi host
            storage_system = esxi_host.configManager.storageSystem
            host_file_sys_vol_mount_info = \
                storage_system.fileSystemVolumeInfo.mountInfo

            datastore_dict = {}
            # Map all filesystems
            for host_mount_info in host_file_sys_vol_mount_info:
                # Extract only VMFS volumes
                if host_mount_info.volume.type == "VMFS":

                    extents = host_mount_info.volume.extent
                    if not args.json:
                        print_fs(host_mount_info)
                    else:
                        datastore_details = {
                            'uuid': host_mount_info.volume.uuid,
                            'capacity': host_mount_info.volume.capacity,
                            'vmfs_version': host_mount_info.volume.version,
                            'local': host_mount_info.volume.local,
                            'ssd': host_mount_info.volume.ssd
                        }

                    extent_arr = []
                    extent_count = 0
                    for extent in extents:
                        if not args.json:
                            print("{}\t{}\t".format(
                                "Extent[" + str(extent_count) + "]:",
                                extent.diskName))
                            extent_count += 1
                        else:
                            # create an array of the devices backing the given
                            # datastore
                            extent_arr.append(extent.diskName)
                            # add the extent array to the datastore info
                            datastore_details['extents'] = extent_arr
                            # associate datastore details with datastore name
                            datastore_dict[host_mount_info.volume.name] = \
                                datastore_details
                    if not args.json:
                        print

            # associate ESXi host with the datastore it sees
            datastores[esxi_host.name] = datastore_dict

        if args.json:
            print(json.dumps(datastores))

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
