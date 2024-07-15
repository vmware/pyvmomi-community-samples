#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2022-2024 Broadcom. All Rights Reserved.
The term "Broadcom" refers to Broadcom Inc. and/or its subsidiaries.

This file includes sample code for vCenter to call Single tier Storagepool
vSAN ESA APIs:

  - AddStoragePoolDisks
  - DeleteStoragePoolDisk
  - UnmountStoragePoolDisk
  - QueryVsanManagedDisks

The script assumes the below cluster setup:
Deployed is a vSAN ESA cluster with minimum node requirement.
There are at least 2 eligible unconsumed disks.
"""

__author__ = 'Broadcom, Inc'

from pyVim.connect import SmartConnect, Disconnect
import sys
import ssl
import atexit
import argparse
import getpass
import http.cookies

import vsanapiutils
import pyVmomi
# Import the vSAN API python bindings and utilities from pyVmomi.
import vsanmgmtObjects
from pyVmomi import vim, vmodl, SoapStubAdapter, VmomiSupport, SessionOrientedStub
from pyVim import task
DECOMISSION_MODE = 'noAction'

def GetArgs():
    """
    Supports the command-line arguments listed below.
    """
    parser = argparse.ArgumentParser(
        description='Process args for vSAN SDK sample application')
    parser.add_argument('-s', '--host', required=True, action='store',
                        help='Remote vCenter to connect to')
    parser.add_argument('-o', '--port', type=int, default=443, action='store',
                        help='Port to connect on')
    parser.add_argument('-u', '--user', required=True, action='store',
                        help='User name to use when connecting to vCenter')
    parser.add_argument('-p', '--password', required=False, action='store',
                        help='Password to use when connecting to vCenter')
    parser.add_argument('--cluster', dest='clusterName', metavar="CLUSTER",
                        default='Vsan2Cluster')
    args = parser.parse_args()
    return args


def GetClusterInstance(clusterName, serviceInstance):
    content = serviceInstance.RetrieveContent()
    searchIndex = content.searchIndex
    datacenters = content.rootFolder.childEntity
    for datacenter in datacenters:
        cluster = searchIndex.FindChild(datacenter.hostFolder, clusterName)
        if cluster is not None:
            return cluster
    return None


"""
Demonstrates AddStoragePoolDisks API
Add disks to Storage Pool
If the task of disk addition fails, any exception will be logged.

Args:
   cluster (vim.ClusterComputeResource): vSAN cluster instance.
   vdms: vsan-disk-management-system MO instance.
   spec (vim.vsan.host.AddStoragePoolDiskSpec): Specifies the data evacuation mode.

Returns:
   None.
"""


def addDiskToStoragePool(cluster, vdms, spec):
    try:
        tsk = vdms.AddStoragePoolDisks([spec])
        addDiskTask = vim.Task(tsk._moId, cluster._stub)
        task.WaitForTask(addDiskTask)
        print("AddDisk to storage pool operation completed")
    except Exception as e:
        print("AddDisk to storage pool operation failed: %s" % e)


"""
Demonstrates QueryDisksForVsan API
Query all vSAN disks

Args:
   host (vim.HostSystem): host reference.

Returns:
   list of all vSAN disks
"""


def queryVsanDisks(host):
    return host.configManager.vsanSystem.QueryDisksForVsan()

"""
Support method helps filter eligible vSAN disks.
Query all vSAN disks

Args:
   host (vim.HostSystem): host reference.

Returns:
   list eligible vSAN disks
"""


def queryEligibleVsanDisks(host, getCanonicalNames=False):
    disks = queryVsanDisks(host)
    eligibleDisks = \
        [d.disk for d in disks if d.state == 'eligible' and d.disk.ssd == True]
    if getCanonicalNames:
        return [d.disk.canonicalName
                for d in disks if d.state == 'eligible' and d.disk.ssd == True]
    else:
        return eligibleDisks


"""
Demonstrates QueryVsanManagedDisks API
Query Storage Pool disks
On success the query returns list of vSAN ESA storage pool disks
If the Query fails, any exception will be logged.

Args:
   vdms: vsan-disk-management-system MO instance.
   host: Specifies the host whose disks are to be queried.
   Returns:
   disks: List of storage pool disks.
"""


def queryStoragePoolDisks(vdms, host):
    spec = vim.vsan.host.QueryVsanDisksSpec()
    spec.vsanDiskType = vim.vsan.host.VsanDiskType("storagePool")
    storagePoolDisks = vdms.QueryVsanManagedDisks(host, spec)
    disks = [disk for storagePool in storagePoolDisks.storagePools for disk
             in storagePool.storagePoolDisks]
    return disks


"""
Demonstrates unmountDiskFromStoragePool API
Unmount disks from storage pool
If the task of disk unmount fails, any exception will be logged.
Args:
   cluster (vim.ClusterComputeResource): vSAN cluster instance.
   vdms: vsan-disk-management-system MO instance.
   spec (vim.vsan.host.DeleteStoragePoolDiskSpec): Specifies the disk to be unmounted.

Returns:
none
"""


def unmountDiskFromStoragePool(cluster, vdms, spec):
    try:
        tsk = vdms.UnmountStoragePoolDisks(cluster, spec)
        unmountDiskTask = vim.Task(tsk._moId, cluster._stub)
        task.WaitForTask(unmountDiskTask)
        print("Unmount disk from storage pool operation completed")
    except Exception as e:
        print("unmount disk from storage pool operation failed: %s" % e)


"""
Demonstrates DeleteStoragePoolDisk API
Removes disks from storage pool
If the task of disk remove fails, any exception will be logged.

Args:
   cluster (vim.ClusterComputeResource): vSAN cluster instance.
   vdms: vsan-disk-management-system MO instance.
   spec (vim.vsan.host.DeleteStoragePoolDiskSpec): Specifies the disk to be removed.

Returns:
none
"""


def removeDiskFromStoragePool(cluster, vdms, spec):
    try:
        tsk = vdms.DeleteStoragePoolDisk(cluster, spec)
        removeDiskTask = vim.Task(tsk._moId, cluster._stub)
        task.WaitForTask(removeDiskTask)
        print("remove disk from storage pool operation completed")
    except Exception as e:
        print("remove disk from storage pool operation failed: %s" % e)


def VpxdStub2HelathStub(stub):
    version1 = pyVmomi.VmomiSupport.newestVersions.Get("vsan")
    sessionCookie = stub.cookie.split('"')[1]
    httpContext = pyVmomi.VmomiSupport.GetHttpContext()
    cookieObj = http.cookies.SimpleCookie()
    cookieObj["vmware_soap_session"] = sessionCookie
    httpContext["cookies"] = cookieObj
    hostname = stub.host.split(":")[0]
    vhStub = pyVmomi.SoapStubAdapter(host=hostname, version =version1, path = "/vsanHealth", poolSize=0)
    vhStub.cookie = stub.cookie
    return vhStub


# Calls VC APIs related to single tier storage
def main():
    args = GetArgs()
    if args.password:
        password = args.password
    else:
        password = getpass.getpass(prompt='Enter password for vCenter %s and '
                                          'user %s: ' % (args.host, args.user))

    # For python 2.7.9 and later, the default SSL context has more strict
    # connection handshaking rule. We may need turn off the hostname checking
    # and client side cert verification.
    context = None
    if sys.version_info[:3] > (2, 7, 8):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    # Fetch a service instance
    si = SmartConnect(host=args.host,
                      user=args.user,
                      pwd=password,
                      port=int(args.port),
                      sslContext=context)

    atexit.register(Disconnect, si)

    apiVersion = vsanapiutils.GetLatestVmodlVersion(args.host, int(args.port))

    cluster = GetClusterInstance(args.clusterName, si)
    if cluster is None:
        print("Cluster {} is not found for {}".format(args.clusterName, args.host))
        return -1

    hosts = cluster.host
    if len(hosts) < 2:
        print("The cluster has not enough host in there. Please add 2 hosts "
              "and try again.")
        return -1

    # Get vSAN disk management system
    # from the vCenter Managed Object references.
    vcMos = vsanapiutils.GetVsanVcMos(
        si._stub, context=context, version=apiVersion)
    vdms = vcMos['vsan-disk-management-system']
    vhstub = VpxdStub2HelathStub(si._stub)
    vcs= vim.cluster.VsanVcClusterConfigSystem('vsan-cluster-config-system', vhstub)

    # Check is vSAN ESA is configured
    if vcs.GetConfigInfoEx(cluster).vsanEsaEnabled != True:
        print("vSAN ESA is not enabled on cluster {}".format(args.clusterName))
        return -1

    # Choose the host of your choice
    firstHost = hosts[1]

    # Step 1) Query vSAN disks and filter out the eligible disks
    #         for the given host. Select the disk of your choice
    #         and invoke the add disks to storage pool API
    # Expectation:
    #        This operation will be successful.
    # Reason:
    #        The disk selected to be added is an eligible disk.
    spec = vim.vsan.host.AddStoragePoolDiskSpec()
    spec.host = firstHost
    eligibleVsanDisks = queryEligibleVsanDisks(spec.host)
    disk = eligibleVsanDisks.pop()
    storagePoolSpec = vim.vsan.host.StoragePoolDisk()
    storagePoolSpec.diskName = disk.canonicalName
    storagePoolSpec.diskType = vim.vsan.host.StoragePoolDiskType('singleTier')
    spec.disks.append(storagePoolSpec)

    print("Eligible vSAN disks : %s", [d.canonicalName for d in eligibleVsanDisks])
    addDiskToStoragePool(cluster, vdms, spec)

    # Step 2) Query storage pool disks and invoke the remove disk from
    #         storage pool API with no action on decommissioning.
    #
    # Expectation:
    #        This operation will be successful.
    storagePoolDisks = queryStoragePoolDisks(vdms, firstHost)
    print("Storage pool disks: ", [d.disk.canonicalName for d in storagePoolDisks])
    spec = vim.vsan.host.DeleteStoragePoolDiskSpec()
    mspec = vim.host.MaintenanceSpec(
        vsanMode=vim.vsan.host.DecommissionMode(objectAction=DECOMISSION_MODE))
    spec.diskUuids = [storagePoolDisks[0].disk.vsanDiskInfo.vsanUuid]
    spec.maintenanceSpec = mspec
    removeDiskFromStoragePool(cluster, vdms, spec)


    # Step 3) Add the other disk to the pool,
    #         Query storage pool disks and invoke unmount disk
    #         from storage pool API with no action on decommissioning
    #         and then invoke the remove disk from datastore API.
    #
    # Expectation:
    #        This operation will be successful.
    # Reason:
    #        The disk can be removed even when it is unmounted from the
    #        storage pool.
    spec = vim.vsan.host.AddStoragePoolDiskSpec()
    spec.host = firstHost
    disk = eligibleVsanDisks.pop()
    storagePoolSpec = vim.vsan.host.StoragePoolDisk()
    storagePoolSpec.diskName = disk.canonicalName
    storagePoolSpec.diskType = vim.vsan.host.StoragePoolDiskType('singleTier')
    spec.disks.append(storagePoolSpec)
    addDiskToStoragePool(cluster, vdms, spec)

    storagePoolDisks = queryStoragePoolDisks(vdms, firstHost)
    spec = vim.vsan.host.DeleteStoragePoolDiskSpec()
    mspec = vim.host.MaintenanceSpec(
        vsanMode=vim.vsan.host.DecommissionMode(objectAction=DECOMISSION_MODE))
    spec.diskUuids = [storagePoolDisks[0].disk.vsanDiskInfo.vsanUuid]
    spec.maintenanceSpec = mspec
    unmountDiskFromStoragePool(cluster, vdms, spec)

    removeDiskFromStoragePool(cluster, vdms, spec)


if __name__ == "__main__":
    main()
