#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Written by Chris Arceneaux
# GitHub: https://github.com/carceneaux
# Email: carceneaux@thinksis.com
# Website: http://arsano.ninja
#
# Note: Example code For testing purposes only
#
# This code has been released under the terms of the Apache-2.0 license
# http://opensource.org/licenses/Apache-2.0

"""
Python program for creating a first class disk (fcd) from a snapshot
"""

import atexit

from tools import cli, tasks
from pyVim import connect
from pyVmomi import vmodl, vim, pbm, VmomiSupport

def get_args():
    """
    Adds additional args for creating a fcd from a snapshot

    -d source_datastore
    -v source_vdisk
    -n snapshot
    -D dest_datastore
    -V dest_vdisk
    """
    parser = cli.build_arg_parser()

    parser.add_argument('-d', '--source_datastore',
                        required=True,
                        action='store',
                        help='Datastore name where source disk is located')

    parser.add_argument('-v', '--source_vdisk',
                        required=True,
                        action='store',
                        help='First Class Disk name with specified snapshot')

    # because -s is reserved for 'service', we use -n for snapshot name
    parser.add_argument('-n', '--snapshot',
                        required=True,
                        action='store',
                        help='Snapshot name to be cloned')

    parser.add_argument('-D', '--dest_datastore',
                        required=True,
                        action='store',
                        help='Datastore name where new disk is located')

    parser.add_argument('-V', '--dest_vdisk',
                        required=True,
                        action='store',
                        help='First Class Disk name to be created')

    # because -s is reserved for 'service' and -p is reserved for 'password'
    parser.add_argument('-e', '--policy',
                        action='store',
                        help='Storage Policy name for new disk. If unset, the default policy of the datastore specified will apply.')

    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)

def get_obj(content, vimtype, name):
    """
    Retrieves the vmware object for the name and type specified
    """
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj

def get_pbm_connection(stub):
    import pyVmomi
    import ssl
    # Make compatible with both Python2/3
    try:
        from http import cookies
    except ImportError:
        import Cookie as cookies

    sessionCookie = stub.cookie.split('"')[1]
    httpContext = VmomiSupport.GetHttpContext()
    cookie = cookies.SimpleCookie()
    cookie["vmware_soap_session"] = sessionCookie
    httpContext["cookies"] = cookie
    VmomiSupport.GetRequestContext()["vcSessionCookie"] = sessionCookie
    hostname = stub.host.split(":")[0]

    context = None
    if hasattr(ssl, "_create_unverified_context"):
        context = ssl._create_unverified_context()
    pbmStub = pyVmomi.SoapStubAdapter(
        host=hostname,
        version="pbm.version.version1",
        path="/pbm/sdk",
        poolSize=0,
        sslContext=context)
    pbmSi = pbm.ServiceInstance("ServiceInstance", pbmStub)
    pbmContent = pbmSi.RetrieveContent()

    return pbmContent

def retrieve_storage_policy(pbmContent,policy):
    """
    Retrieves the vmware object for the storage policy specified
    """
    # Set PbmQueryProfile
    pm = pbmContent.profileManager

    # Retrieving Storage Policies
    profileIds = pm.PbmQueryProfile(resourceType=pbm.profile.ResourceType(
        resourceType="STORAGE"), profileCategory="REQUIREMENT"
    )
    if len(profileIds) > 0:
        profiles = pm.PbmRetrieveContent(profileIds=profileIds)
    else:
        raise RuntimeError("No Storage Policies found.")

    # Searching for Storage Policy
    profile = None
    for p in profiles:
        if p.name == policy:
            profile = p
            break
    if not profile:
        raise RuntimeError("Storage Policy specified not found.")
    
    return profile

def retrieve_fcd(content,datastore,vdisk):
    """
    Retrieves the vmware object for the first class disk specified
    """
    # Set vStorageObjectManager
    storage = content.vStorageObjectManager

    # Retrieve First Class Disks    
    disk = None
    for d in storage.ListVStorageObject(datastore):        
        disk_info = storage.RetrieveVStorageObject(d,datastore)
        if disk_info.config.name == vdisk:
            disk = disk_info
            break
    if not disk:
        raise RuntimeError("First Class Disk not found.")
    return disk

def retrieve_snapshot(content,datastore,vdisk,snapshot):
    """
    Retrieves the vmware object for the snapshot specified
    """
    # Set vStorageObjectManager
    storage = content.vStorageObjectManager

    # Retrieve Snapshot    
    snap = None
    for s in storage.RetrieveSnapshotInfo(vdisk.config.id,datastore).snapshots:
        if s.description == snapshot:
            snap = s.id
            break
    if not snap:
        raise RuntimeError("Snapshot not found.")
    return snap

def main():
    """
    Simple command-line program for deleting a snapshot of a first class disk.
    """

    args = get_args()

    try:
        if args.disable_ssl_verification:
            service_instance = connect.SmartConnectNoSSL(host=args.host,
                                                         user=args.user,
                                                         pwd=args.password,
                                                         port=int(args.port))
        else:
            service_instance = connect.SmartConnect(host=args.host,
                                                    user=args.user,
                                                    pwd=args.password,
                                                    port=int(args.port))

        atexit.register(connect.Disconnect, service_instance)

        content = service_instance.RetrieveContent()

        # Connect to SPBM Endpoint
        pbmContent = get_pbm_connection(service_instance._stub)

        # Retrieving Storage Policy
        if args.policy:
            p = retrieve_storage_policy(pbmContent,args.policy)
            policy = [vim.vm.DefinedProfileSpec( profileId=p.profileId.uniqueId )]
        else:
            policy = None

        # Retrieve Source Datastore Object
        source_datastore = get_obj(content, [vim.Datastore], args.source_datastore)

        # Retrieve Source FCD Object
        source_vdisk = retrieve_fcd(content,source_datastore,args.source_vdisk)

        # Retrieve Snapshot Object
        snapshot = retrieve_snapshot(content,source_datastore,source_vdisk,args.snapshot)

        # Retrieve Destination Datastore Object
        dest_datastore = get_obj(content, [vim.Datastore], args.dest_datastore)

        # Create FCD from Snapshot
        storage = content.vStorageObjectManager
        if policy:
            task = storage.CreateDiskFromSnapshot_Task(
                                                    source_vdisk.config.id,
                                                    dest_datastore,
                                                    snapshot,
                                                    args.dest_vdisk,
                                                    policy)
        else:
            task = storage.CreateDiskFromSnapshot_Task(
                                                    source_vdisk.config.id,
                                                    dest_datastore,
                                                    snapshot,
                                                    args.dest_vdisk)        
        tasks.wait_for_tasks(service_instance, [task])

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()