#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2020-2024 Broadcom. All Rights Reserved.
Broadcom Confidential. The term "Broadcom" refers to Broadcom Inc.

This file includes sample code for vCenter to call WhatIfDecomDiskAndDiskGroup
vSAN APIs:

  - PerformResourceCheck
  - GetResourceCheckStatus
  - RemoveDiskEx
  - RemoveDiskMappingEx
  - RebuildDiskMapping
  - UnmountDiskMappingEx

Cluster setup required for this sample API:
- 4 node cluster with vsan enabled
- Create 1 diskGroup with 1 cache and 2 capacity disks for first 3 nodes
(use cluster instance to find first 3 hosts)
- No diskGroup on fourth host at the beginning but it has 3
spare disks to form a diskGroup (1 cache + 2 capacity) later.
- Deploy 1 VM on the cluster
- VM Policy is FTT = 1
"""

__author__ = 'Broadcom, Inc'

from pyVim.connect import SmartConnect, Disconnect
import time
import sys
import ssl
import atexit
import argparse
import getpass
if sys.version[0] < '3':
   input = raw_input

# Import the vSAN API python bindings and utilities.
import pyVmomi
import vsanmgmtObjects
import vsanapiutils

from pyVmomi import vim, vmodl, SoapStubAdapter, VmomiSupport
from pyVim import task


def GetArgs():
   """
   Supports the command-line arguments listed below.
   """
   parser = argparse.ArgumentParser(
       description='Process args for vSAN SDK sample application')
   parser.add_argument('-s', '--host', required=True, action='store',
                       help='Remote host to connect to')
   parser.add_argument('-o', '--port', type=int, default=443, action='store',
                       help='Port to connect on')
   parser.add_argument('-u', '--user', required=True, action='store',
                       help='User name to use when connecting to host')
   parser.add_argument('-p', '--password', required=False, action='store',
                       help='Password to use when connecting to host')
   parser.add_argument('--cluster', dest='clusterName', metavar="CLUSTER",
                      default='VSAN-Cluster')
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
Run what-if resource check for a capacity disk or a diskGroup
with the given resource check spec.
Args:
   cluster (vim.ClusterComputeResource): vSAN cluster which owns
                                         the disk or diskGroup.
   vscrcs: "vsan-cluster-resource-check-system" MO instance.
   spec (vim.vsan.ResourceCheckSpec): The resource check spec.
Returns:
   0: resource check result is pass or unknown.
      The main workflow can still proceed.
   -1: resource check result indicates there is not enough resource
      in the cluster for related operations so the main workflow
      should be aborted.
"""
def RunResourceCheck(cluster, vscrcs, spec):
   try:
      tsk = vscrcs.PerformResourceCheck(spec, cluster)
      resourceCheckTask = vim.Task(tsk._moId, cluster._stub)
      task.WaitForTask(resourceCheckTask)
      resRes = vscrcs.GetResourceCheckStatus(spec, cluster)
   except Exception as e:
      print("Runtime error during resource check: %s" % e)

   # Usually the main workflow should be aborted only when the
   # resource check task finishes successfully and the result shows 'red'
   # status which clearly indicates there is not enough resource
   # in the cluster for related operations.
   #
   # If the resource check task failed to complete somehow,
   # we may still want to give it a try for the actual operation
   # (e.g. remove a disk-group) and continue the main workflow
   # (i.e. a more aggressive way with unknown resource check result).
   if resRes is None:
      return 0

   if (resRes.status == vim.vsan.ResourceCheckStatusType(
                           "resourceCheckCompleted") and
       resRes.result is not None and
       resRes.result.status == "red"):
      print("Disk data evacuation resource check "
            "completed but the result is red.")
      return -1
   else:
       print("Disk data evacuation resource check: %s" %
             resRes.status)
       return 0

"""
Remove a single capacity disk from a diskGroup.
If the task of disk removal fails, any exception will be logged.

Args:
   cluster (vim.ClusterComputeResource): vSAN cluster instance.
   vdms: vsan-disk-management-system MO instance.
   diskToBeRemoved (vim.host.ScsiDisk): capacity disk to be removed.
   mSpec (vim.host.MaintenanceSpec): Specifies the data evacuation mode.

Returns:
   None.
"""
def InvokeRemoveDiskExApi(cluster, vdms, diskToBeRemoved, mSpec):
   try:
      tsk = vdms.RemoveDiskEx(cluster, [diskToBeRemoved], mSpec)
      removeDiskTask = vim.Task(tsk._moId, cluster._stub)
      print("Starting remove disk task.")
      task.WaitForTask(removeDiskTask)
   except Exception as e:
      print("RemoveDisk operation failed: %s" % e)

"""
Remove vSAN disk mapping(s) from use in a vSAN cluster with the
specified data evacuation mode. If the task of diskgroup
removal fails, any exception will be logged.

Args:
   cluster (vim.ClusterComputeResource): vSAN cluster instance.
   vdms: vsan-disk-management-system MO instance.
   disksMaps(vim.vsan.host.DiskMapping[]): list of disk mapping(s)
                                           to be removed.
   mSpec (vim.host.MaintenanceSpec): Specifies the data evacuation mode.

Returns:
   None.
"""
def InvokeRemoveDiskMappingApi(cluster, vdms, disksMaps, mSpec):
   try:
      tsk = vdms.RemoveDiskMappingEx(cluster, disksMaps, mSpec)
      removeDiskMappingTask = vim.Task(tsk._moId, cluster._stub)
      task.WaitForTask(removeDiskMappingTask)
   except Exception as e:
      print("RemoveDiskMapping operation failed: %s" % e)

"""
Unmount vSAN disk mapping(s) in a vSAN cluster with the specified
data evacuation mode. If the task of unmount disk fails,
any exception will be logged.

Args:
   cluster (vim.ClusterComputeResource): vSAN cluster instance.
   vdms: vsan-disk-management-system MO instance.
   disksMaps (vim.vsan.host.DiskMapping[]): list of disk mapping(s)
                                            to be unmounted.
   mSpec (vim.host.MaintenanceSpec): Specifies the data evacuation mode.

Returns:
   None.
"""
def InvokeUnmountDiskMappingExApi(cluster, vdms, disksMaps, mSpec):
   try:
      tsk = vdms.UnmountDiskMappingEx(cluster, disksMaps, mSpec)
      unmountDiskMappingTask = vim.Task(tsk._moId, cluster._stub)
      task.WaitForTask(unmountDiskMappingTask)
   except Exception as e:
      print("UnmountDiskMapping operation failed: %s" % e)

"""
Rebuild an existing vSAN disk mapping on the specified host.
If the task of rebuilt disk mapping fails, any exception
will be logged.

Args:
   cluster (vim.ClusterComputeResource): vSAN cluster instance.
   host: Target host which owns the diskGroup to rebuild.
   vdms: vsan-disk-management-system MO instance.
   disksMap (vim.vsan.host.DiskMapping): disk mapping to be rebuilt
                                         from vSAN usage.
   mSpec (vim.host.MaintenanceSpec): Specifies the data evacuation mode.

Returns:
   None.
"""
def InvokeRebuildDiskMappingApi(cluster, host, vdms, disksMap, mSpec):
   try:
      tsk = vdms.RebuildDiskMapping(host, disksMap, mSpec)
      rebuildDiskMappingTask = vim.Task(tsk._moId, cluster._stub)
      task.WaitForTask(rebuildDiskMappingTask)
   except Exception as e:
      print("RebuildDiskMapping operation failed: %s" % e)

"""
Create a new vSAN diskGroup on specified host. If the task of
initializing disk mapping fails, any exception will be logged.

Args:
   cluster (vim.ClusterComputeResource): vSAN cluster instance.
   host: Target host which will own created diskGroup.
   vdms: vsan-disk-management-system MO instance.

Returns:
   None.
"""
def CreateDiskMapping(cluster, host, vdms):
   try:
      cacheDisk = None
      capacityDisk = []
      disks = host.configManager.vsanSystem.QueryDisksForVsan()

      for result in disks:
         if (result.state.strip() == "eligible"):
            if result.disk.ssd:
               cacheDisk = result.disk
            else:
               capacityDisk.append(result.disk)

      if cacheDisk is not None and len(capacityDisk) > 0:
         spec = vim.vsan.host.DiskMappingCreationSpec(
            cacheDisks = [cacheDisk],
            capacityDisks = capacityDisk,
            creationType = "allFlash",
            host = host
         )

      tsk = vdms.InitializeDiskMappings(spec)
      diskMapCreationTask = vim.Task(tsk._moId, cluster._stub)
      task.WaitForTask(diskMapCreationTask)
   except Exception as e:
      print("Diskmapping creation task failed: %s" % e)


def main():
   args = GetArgs()
   if args.password:
      password = args.password
   else:
      password = getpass.getpass(prompt='Enter password for host %s and '
                                        'user %s: ' % (args.host,args.user))

   # For python 2.7.9 and later, the default SSL context has more strict
   # connection handshaking rule. We may need turn off the hostname checking
   # and client side cert verification.
   context = None
   if sys.version_info[:3] > (2,7,8):
      context = ssl.create_default_context()
      context.check_hostname = False
      context.verify_mode = ssl.CERT_NONE

   si = SmartConnect(host=args.host,
                     user=args.user,
                     pwd=password,
                     port=int(args.port),
                     sslContext=context)

   atexit.register(Disconnect, si)

   # Detecting whether the host is vCenter or ESXi.
   aboutInfo = si.content.about
   apiVersion = vsanapiutils.GetLatestVmodlVersion(args.host, int(args.port))

   if aboutInfo.apiType != 'VirtualCenter':
      print("Host %s is not a VC host. Please run this script on a VC host.",
             args.host)
      return
   else:
      majorApiVersion = aboutInfo.apiVersion.split('.')[0]
      if int(majorApiVersion) < 6:
         print('The Virtual Center with version %s ( <6.0) is not supported.'
               % aboutInfo.apiVersion)
         return -1

      cluster = GetClusterInstance(args.clusterName, si)
      if cluster is None:
         print("Cluster %s is not found for %s", args.clusterName, args.host)
         return -1

      hosts=cluster.host
      if len(hosts) < 4:
         print("The cluster has not enough host in there. Please add 4 hosts "
               "and try again.")
         return -1

      # Get vSAN cluster resource check systems and disk management system
      # from the vCenter Managed Object references.
      vcMos = vsanapiutils.GetVsanVcMos(
            si._stub, context=context, version=apiVersion)
      vscrcs = vcMos['vsan-cluster-resource-check-system']
      vdms = vcMos['vsan-disk-management-system']

      firstHost = hosts[0]

      mSpec = vim.host.MaintenanceSpec(
                 vsanMode = vim.vsan.host.DecommissionMode(
                               objectAction = "evacuateAllData"))
      disksMaps = firstHost.configManager.vsanSystem.config.storageInfo.diskMapping
      diskUuid = disksMaps[0].nonSsd[0].vsanDiskInfo.vsanUuid
      spec = vim.vsan.ResourceCheckSpec(operation="DiskDataEvacuation",
                                        entities=[diskUuid],
                                        maintenanceSpec=mSpec)

      # Step 1) Check resource precheck results for evacuateAllData decom
      #         mode on capacity disk of diskGroup on the first host.
      #         If resource precheck result is pass, the test will
      #         proceed to remove this capacity disk.
      # Expectation:
      #        This operation will be successful.
      # Reason:
      #        Host has 2 capacity disks and 1 cache in diskGroup so
      #        by removing one capacity disk and moving data to
      #        another capacity disk still FTT = 1 holds.
      print("Perform resource precheck for a capacity disk on host %s."
            % firstHost.name)
      RunResourceCheck(cluster, vscrcs, spec)
      print("Removing capacity disk from host %s  with evacuateAll mode."
            % firstHost.name)
      InvokeRemoveDiskExApi(cluster, vdms, disksMaps[0].nonSsd[0], mSpec)

      # Step 2) Check Resource precheck results on diskGroup with
      #         evacuateAllData mode on first host having 1
      #         cache and 1 capacity disk. After resource precheck,
      #         try removing same diskGroup for the first host.
      # Expectation:
      #        This operation will fail. Resource precheck result will be 'red',
      #        which indicates the removal of this diskGroup will fail.
      #        If we continue to remove the diskGroup, it will fail as expected.
      # Reason:
      #        In the cluster, 3 hosts have 1 diskGroup and FTT = 1. By removing
      #        diskGroup on one host, there is no diskGroup left to move data.
      #        FTT policy will be violated as there is not enough fault domain
      #        left to hold FTT = 1 so this operation will fail.
      diskUuid = disksMaps[0].ssd.vsanDiskInfo.vsanUuid
      print("Perform resource precheck for disk group on host %s."
            % firstHost.name)
      spec = vim.vsan.ResourceCheckSpec(operation="DiskDataEvacuation",
                                        entities=[diskUuid],
                                        maintenanceSpec=mSpec)
      RunResourceCheck(cluster, vscrcs, spec)
      print("Removing disk Mapping on host %s with evacuateAll mode."
            % firstHost.name)
      InvokeRemoveDiskMappingApi(cluster, vdms, disksMaps, mSpec)

      # Step 3) Create a diskGroup with 1 cache and 2 capacity disks for
      #         fourth host in cluster.
      # Expectation:
      #        This operation will succeed. The fourth host has 1
      #        cache and 2 capacity disks to create a diskGroup.
      # Result:
      #        A diskGroup is created on fourt host. The cluster will
      #        have 4 hosts each having 1 diskGroup.
      print("Creating disk group on host %s" % hosts[3].name)
      CreateDiskMapping(cluster, hosts[3], vdms)

      # Step 4) Check Resource precheck results for diskGroup on first host
      #         having 1 cache and 1 capacity disk with evacuateAllData
      #         mode. After resource check, try removing same diskGroup
      #         for the first host.
      # Expectation:
      #        This operation will succeed.
      # Reason:
      #        The cluster has 1 diskGroup per 4 hosts and FTT = 1.
      #        By removing diskGroup on one host, since we added a
      #        diskGroup on fourth host, data will be moved to another
      #        diskGroup and FTT = 1 is valid.
      disksMaps = firstHost.configManager.vsanSystem.config.storageInfo.diskMapping
      diskUuid = disksMaps[0].ssd.vsanDiskInfo.vsanUuid
      print("Perform resource precheck for disk group on host %s."
            % firstHost.name)
      spec = vim.vsan.ResourceCheckSpec(operation="DiskDataEvacuation",
                                        entities=[diskUuid],
                                        maintenanceSpec=mSpec)
      RunResourceCheck(cluster, vscrcs, spec)
      print("Removing disk Mapping on host %s with evacuateAll mode."
            % firstHost.name)
      InvokeRemoveDiskMappingApi(cluster, vdms, disksMaps, mSpec)

      secondHost = hosts[1]

      # Step 5) Perform RebuildDiskMapping on second host with
      #         ensureAccessibilty mode.
      # Expectation:
      #        This operation will succeed.
      # Result:
      #        There are 3 hosts with 1 diskGroup and all vSAN
      #        objects are still accessible during/after the rebuild operation.
      mSpec = vim.host.MaintenanceSpec(
                 vsanMode = vim.vsan.host.DecommissionMode(
                               objectAction = "ensureObjectAccessibility"))
      disksMaps = secondHost.configManager.vsanSystem.config.storageInfo.diskMapping
      print("Rebuild disk Mapping on host %s with ensure accessibilty mode."
            % secondHost.name)
      InvokeRebuildDiskMappingApi(cluster, secondHost, vdms, disksMaps[0], mSpec)

      # Step 6) Unmount DiskMapping on second host with noAction mode.
      # Expectation:
      #        This operation will succeed.
      # Result:
      #        As data evacuation mode is no Action operation will always succeed.
      mSpec = vim.host.MaintenanceSpec(
                 vsanMode = vim.vsan.host.DecommissionMode(
                               objectAction = "noAction"))
      disksMaps = secondHost.configManager.vsanSystem.config.storageInfo.diskMapping
      print("Unmount disk Mapping on host %s with no action mode."
            % secondHost.name)
      InvokeUnmountDiskMappingExApi(cluster, vdms, disksMaps, mSpec)

      print("Invoking WhatIfDecomDiskAndDiskGroup APIs completed successfully.")

if __name__ == "__main__":
   main()

