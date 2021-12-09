#!/usr/bin/env python
"""
 Written by Tony Allen
 Github: https://github.com/stormbeard
 Blog: https://stormbeard.net/
 This code has been released under the terms of the Apache 2 licenses
 http://www.apache.org/licenses/LICENSE-2.0.html

 Script to deploy VM via a single .ovf and a single .vmdk file.
"""
from os import system, path
from sys import exit
from threading import Thread
from time import sleep
from pyVmomi import vim
from tools import cli, service_instance


def get_ovf_descriptor(ovf_path):
    """
    Read in the OVF descriptor.
    """
    if path.exists(ovf_path):
        with open(ovf_path, 'r') as ovf_file:
            try:
                ovfd = ovf_file.read()
                ovf_file.close()
                return ovfd
            except Exception:
                print("Could not read file: %s" % ovf_path)
                exit(1)


def get_obj_in_list(obj_name, obj_list):
    """
    Gets an object out of a list (obj_list) whose name matches obj_name.
    """
    for obj in obj_list:
        if obj.name == obj_name:
            return obj
    print("Unable to find object by the name of %s in list:\n%s" %
          (obj_name, map(lambda o: o.name, obj_list)))
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
        print("No datastores found in DC (%s)." % datacenter_obj.name)
        exit(1)

    # Get cluster object.
    cluster_list = datacenter_obj.hostFolder.childEntity
    if args.cluster_name:
        cluster_obj = get_obj_in_list(args.cluster_name, cluster_list)
    elif len(cluster_list) > 0:
        cluster_obj = cluster_list[0]
    else:
        print("No clusters found in DC (%s)." % datacenter_obj.name)
        exit(1)

    # Generate resource pool.
    resource_pool_obj = cluster_obj.resourcePool

    return {"datacenter": datacenter_obj,
            "datastore": datastore_obj,
            "resource pool": resource_pool_obj}


def keep_lease_alive(lease):
    """
    Keeps the lease alive while POSTing the VMDK.
    """
    while True:
        sleep(5)
        try:
            # Choosing arbitrary percentage to keep the lease alive.
            lease.HttpNfcLeaseProgress(50)
            if lease.state == vim.HttpNfcLease.State.done:
                return
            # If the lease is released, we get an exception.
            # Returning to kill the thread.
        except Exception:
            return


def main():
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.VMDK_PATH, cli.Argument.OVF_PATH)
    parser.add_optional_arguments(
        cli.Argument.DATACENTER_NAME, cli.Argument.DATASTORE_NAME, cli.Argument.CLUSTER_NAME)
    args = parser.get_args()
    si = service_instance.connect(args)
    ovfd = get_ovf_descriptor(args.ovf_path)
    objs = get_objects(si, args)
    manager = si.content.ovfManager
    spec_params = vim.OvfManager.CreateImportSpecParams()
    import_spec = manager.CreateImportSpec(ovfd,
                                           objs["resource pool"],
                                           objs["datastore"],
                                           spec_params)
    lease = objs["resource pool"].ImportVApp(import_spec.importSpec,
                                             objs["datacenter"].vmFolder)
    while True:
        if lease.state == vim.HttpNfcLease.State.ready:
            # Assuming single VMDK.
            url = lease.info.deviceUrl[0].url.replace('*', args.host)
            # Spawn a dawmon thread to keep the lease active while POSTing
            # VMDK.
            keepalive_thread = Thread(target=keep_lease_alive, args=(lease,))
            keepalive_thread.start()
            # POST the VMDK to the host via curl. Requests library would work
            # too.
            curl_cmd = (
                "curl -Ss -X POST --insecure -T %s -H 'Content-Type: \
                application/x-vnd.vmware-streamVmdk' %s" %
                (args.vmdk_path, url))
            system(curl_cmd)
            lease.HttpNfcLeaseComplete()
            keepalive_thread.join()
            return 0
        elif lease.state == vim.HttpNfcLease.State.error:
            print("Lease error: " + lease.state.error)
            exit(1)


if __name__ == "__main__":
    exit(main())
