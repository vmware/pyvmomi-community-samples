#!/usr/bin/env python
"""
 Written by Tony Allen
 Github: https://github.com/stormbeard
 Blog: https://stormbeard.net/
 This code has been released under the terms of the Apache 2 licenses
 http://www.apache.org/licenses/LICENSE-2.0.html

 Script to deploy VM via a single .ovf and a single .vmdk file.
"""
import ssl
from os import system, path, SEEK_END
from sys import exit, stderr
from threading import Thread
from time import sleep
from argparse import ArgumentParser
from getpass import getpass

from pyVim import connect
from pyVmomi import vim

import urllib2


# http://stackoverflow.com/questions/5925028/urllib2-post-progress-monitoring
class Progress(object):
    def __init__(self):
        self._seen = 0.0

    def update(self, total, size, name):
        self._seen += size
        pct = (self._seen / total) * 100.0
        print '%s progress: %.2f' % (name, pct)


class file_with_callback(file):
    def __init__(self, path, mode, callback, *args):
        file.__init__(self, path, mode)
        self.seek(0, SEEK_END)
        self._total = self.tell()
        self.seek(0)
        self._callback = callback
        self._args = args

    def __len__(self):
        return self._total

    def read(self, size):
        data = file.read(self, size)
        self._callback(self._total, len(data), *self._args)
        return data


# end of stack overflow reference

def get_args():
    """
    Get CLI arguments.
    """
    parser = ArgumentParser(description='Arguments for talking to vCenter')

    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='vSphere service to connect to.')

    parser.add_argument('-o', '--port',
                        type=int,
                        default=443,
                        action='store',
                        help='Port to connect on.')

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='Username to use.')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to use.')

    parser.add_argument('--datacenter_name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the Datacenter you\
                          wish to use. If omitted, the first\
                          datacenter will be used.')

    parser.add_argument('--datastore_name',
                        required=False,
                        action='store',
                        default=None,
                        help='Datastore you wish the VM to be deployed to. \
                          If left blank, VM will be put on the first \
                          datastore found.')

    parser.add_argument('--cluster_name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the cluster you wish the VM to\
                          end up on. If left blank the first cluster found\
                          will be used')

    parser.add_argument('--host_name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the host you wish the VM to\
                          end up on. If left blank the first cluster found\
                          will be used')

    parser.add_argument('--folder_name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the VM folder you wish the VM to\
                          end up in. \
                          If left blank it will not be in a folder.')

    parser.add_argument('-n', '--vm_name',
                        required=False,
                        action='store',
                        default='',
                        help='Name of the VM after deploy')

    parser.add_argument('-v', '--vmdk_path',
                        required=True,
                        action='store',
                        default=None,
                        help='Path of the VMDK file to deploy.')

    parser.add_argument('-f', '--ovf_path',
                        required=True,
                        action='store',
                        default=None,
                        help='Path of the OVF file to deploy.')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass(prompt='Enter password: ')

    return args


def get_ovf_descriptor(ovf_path):
    """
    Read in the OVF descriptor.
    """
    if path.exists(ovf_path):
        with open(ovf_path, 'r') as f:
            try:
                ovfd = f.read()
                f.close()
                return ovfd
            except:
                print "Could not read file: %s" % ovf_path
                exit(1)


def get_obj_in_list(obj_name, obj_list):
    """
    Gets an object out of a list (obj_list) whos name matches obj_name.
    """
    for o in obj_list:
        if o.name == obj_name:
            return o
    print ("Unable to find object by the name of %s in list:\n%s" %
           (o.name, map(lambda o: o.name, obj_list)))
    exit(1)


def get_objects(si, args):
    """
    Return a dict containing the necessary objects for deployment.
    """
    # Get datacenter object.
    datacenter_list = si.content.rootFolder.childEntity
    if args.datacenter_name:
        datacenter_obj = get_obj_in_list(args.datacenter_name, datacenter_list)
    else:
        datacenter_obj = datacenter_list[0]

    # Get datastore object.
    datastore_list = datacenter_obj.datastoreFolder.childEntity
    if args.datastore_name:
        datastore_obj = get_obj_in_list(args.datastore_name, datastore_list)
    elif len(datastore_list) > 0:
        datastore_obj = datastore_list[0]
    else:
        print "No datastores found in DC (%s)." % datacenter_obj.name

    # Get vm folder object
    vmFolder_List = datacenter_obj.vmFolder.childEntity
    if args.folder_name:
        folder_obj = get_obj_in_list(args.folder_name, vmFolder_List)
    elif len(vmFolder_List) > 0:
        folder_obj = vmFolder_List[0]
    else:
        print "No folder found in DC (%s)." % datacenter_obj.name

    # Get cluster object.
    cluster_list = datacenter_obj.hostFolder.childEntity
    if args.cluster_name:
        cluster_obj = get_obj_in_list(args.cluster_name, cluster_list)
    elif len(cluster_list) > 0:
        cluster_obj = cluster_list[0]
    else:
        print "No clusters found in DC (%s)." % datacenter_obj.name

    # Get host object.
    host_list = cluster_obj.host
    if args.host_name:
        host_obj = get_obj_in_list(args.host_name, host_list)
    elif len(cluster_list) > 0:
        host_obj = host_list[0]
    else:
        print "No host found in Cluster (%s)." % cluster_obj.name

    # Generate resource pool.
    resource_pool_obj = cluster_obj.resourcePool

    return {"datacenter": datacenter_obj,
            "datastore": datastore_obj,
            "resource pool": resource_pool_obj,
            "folder": folder_obj,
            "host": host_obj}


def keep_lease_alive(lease):
    """
    Keeps the lease alive while POSTing the VMDK.
    """
    while(True):
        sleep(5)
        try:
            # Choosing arbitrary percentage to keep the lease alive.
            lease.HttpNfcLeaseProgress(50)
            if (lease.state == vim.HttpNfcLease.State.done):
                return
            # If the lease is released, we get an exception.
            # Returning to kill the thread.
        except:
            return


def main():
    args = get_args()
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        si = connect.SmartConnect(host=args.host,
                                  user=args.user,
                                  pwd=args.password,
                                  port=args.port,
                                  sslContext=ctx)
    except:
        print "Unable to connect to %s" % args.host
        exit(1)
    objs = get_objects(si, args)
    deploy(args.host, si, args.ovf_path, args.vmdk_path, args.vm_name,
           objs["resource pool"], objs["datastore"],
           objs["folder"], objs["host"])
    connect.Disconnect(si)


def deploy(host, si, ovf_path, vmdk_path,
           vm_name, resoure_pool, datastore, folder, esxhost):
    ovfd = get_ovf_descriptor(ovf_path)

    manager = si.content.ovfManager
    spec_params = vim.OvfManager.CreateImportSpecParams()
    spec_params.entityName = vm_name
    import_spec = manager.CreateImportSpec(ovfd,
                                           resoure_pool,
                                           datastore,
                                           spec_params)
    lease = resoure_pool.ImportVApp(import_spec.importSpec, folder=folder, host=esxhost)
    while(True):
        if (lease.state == vim.HttpNfcLease.State.ready):
            # Assuming single VMDK.
            url = lease.info.deviceUrl[0].url.replace('*', host)
            # Spawn a dawmon thread to keep the lease active while POSTing
            # VMDK.
            keepalive_thread = Thread(target=keep_lease_alive, args=(lease,))
            keepalive_thread.start()
            # POST the VMDK to the host via curl. Requests library would work
            # too.

            # New method using urllib2
            path = vmdk_path
            progress = Progress()
            stream = file_with_callback(path, 'rb', progress.update, path)
            req = urllib2.Request(url, stream)

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            res = urllib2.urlopen(req, context=ctx)

            lease.HttpNfcLeaseComplete()
            keepalive_thread.join()
            return 0
        elif (lease.state == vim.HttpNfcLease.State.error):
            print "Lease error: " + lease.state.error
            exit(1)

if __name__ == "__main__":
    exit(main())
