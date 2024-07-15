#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2020-2024 Broadcom. All Rights Reserved.
The term "Broadcom" refers to Broadcom Inc. and/or its subsidiaries.

This file includes sample codes for vCenter side vSAN SharedWitness API
accessing.

To provide an example of vCenter side vSAN SharedWitness API access,
it shows how to configure shared witness in the following scenarios:
1. For replacing multiple robo clusters of witnees into one sharedwitness
 in batch:
  Requirements: one sharedwitness and one or more robo clusters.
  API: ReplaceWitnessHostForClusters of the VsanVcStretchedClusterSystem MO.
2. For converting one or more regular two-node vSAN clusters to robo clusters
 sharing the same witness in batch:
   Requirements: one sharedwitness and one or more regular two-node
                 vSAN clusters.
   API: AddWitnessHostForClusters of the VsanVcStretchedClusterSystem MO.
"""

__author__ = 'Broadcom, Inc'

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import sys
import ssl
import atexit
import argparse
import getpass
from distutils.version import LooseVersion

# Import the vSAN API python bindings and utilities.
import pyVmomi
import vsanmgmtObjects
import vsanapiutils

def GetArgs():
   """
   Supports the command-line arguments listed below.
   """
   parser = argparse.ArgumentParser(
       description='Process args for vSAN SDK sample application')
   parser.add_argument('-s', '--host', required=True, action='store',
                       help='Remote VirtualCenter to connect to')
   parser.add_argument('-o', '--port', type=int, default=443, action='store',
                       help='Port to connect on')
   parser.add_argument('-w', '--witness', required=True, action='store',
                       help='Remote witness node to connect to')
   parser.add_argument('-u', '--user', required=True, action='store',
                       help='User name to use when connecting to host')
   parser.add_argument('-p', '--password', required=False, action='store',
                       help='Password to use when connecting to host')
   parser.add_argument('--roboclusters', dest='roboClusters', action='store',
                       help='Cluster name list of candidate vSAN robo clusters,'
                       ' format: "cluster_1, cluster_2, ..."')
   parser.add_argument('--normalclusters', dest='normalClusters', action='store',
                       help='Cluster name list of candidate regular two-node vSAN'
                       ' clusters, format: "cluster_1, cluster_2, ..."')
   args = parser.parse_args()
   return args


def getComputeInstance(entityName, serviceInstance):
   content = serviceInstance.RetrieveContent()
   searchIndex = content.searchIndex
   datacenters = content.rootFolder.childEntity
   for datacenter in datacenters:
      instance = searchIndex.FindChild(datacenter.hostFolder, entityName)
      if instance is not None:
         return instance
   return None


def getClusterInstances(clusterNames, serviceInstance):
   clusters = []
   content = serviceInstance.RetrieveContent()
   searchIndex = content.searchIndex
   datacenters = content.rootFolder.childEntity
   dc = None
   for clusterName in clusterNames:
      cluster = getComputeInstance(clusterName, serviceInstance)
      if not cluster:
         msg = 'ERROR: Cluster %s is not found for %s' % clusterName
         sys.exit(msg)
      clusters.append(cluster)
   return clusters

def checkCompatibility(si, vscs, clusterRefs, witness):
   compatCheckResult = \
      vscs.QuerySharedWitnessCompatibility(witness, clusterRefs)
   if not compatCheckResult.witnessHostCompatibility.compatible:
      msg = "ERROR: target host %s doesn't have shared witness capability: %s" \
            % (witness.name,
            compatCheckResult.witnessHostCompatibility.incompatibleReasons)
      sys.exit(msg)
   for clusterCompResult in compatCheckResult.roboClusterCompatibility:
      if not clusterCompResult.compatible:
         clusterMo = vim.ClusterComputeResource(clusterCompResult.entity._moId,
                                                si._stub)
         msg = "ERROR: cluster %s could not meet shared witness capability" \
               " requirement: %s" % \
               (clusterMo.name, clusterCompResult.incompatibleReasons)
         sys.exit(msg)

def convertToRoboClusterInBatch(si, vscs, witness, clusterRefs):
   """ Convert multiple two-node vsan clusters to robo clusters
       that share the same witness in batch.

   Requirements:
      1. The candidate cluster must be a two-node cluster with vsan enable.
      2. There is no network isolation between witness and the multiple
      clusters given.
   """
   checkCompatibility(si, vscs, clusterRefs, witness)
   for cluster in clusterRefs:
      if len(vscs.GetWitnessHosts(cluster)) != 0:
         msg = "ERROR: cluster %s is not a regular vSAN cluster" % cluster.name
         sys.exit(msg)
   print("Converting normal vSAN clusters(2 nodes) '%s' to robo clusters" \
         " with shared witness %s" % \
         ([cluster.name for cluster in clusterRefs], witness.name))
   spec = vim.vsan.VsanVcStretchedClusterConfigSpec(
      witnessHost = witness,
      clusters = [vim.cluster.VsanStretchedClusterConfig(
         cluster = cluster,
         preferredFdName= 'fd1',
         faultDomainConfig=
         vim.cluster.VSANStretchedClusterFaultDomainConfig(
            firstFdName = 'fd1',
            firstFdHosts = [cluster.host[0]],
            secondFdName = 'fd2',
            secondFdHosts = [cluster.host[1]],
         ),
      ) for cluster in clusterRefs]
   )
   addWitnessTask = vscs.AddWitnessHostForClusters(spec)
   vsanapiutils.WaitForTasks([addWitnessTask], si)

def replaceWitnessInBatch(si, vscs, witness, clusterRefs):
   """ Replace witness with the same Shared witness in batches for
       for multiple robo clusters in one operation.

   Requirements:
      1. The candidate cluster must be vSAN robo cluster.
      2. There is no network isolation between witness and the multiple
      clusters given.
   """
   checkCompatibility(si, vscs, clusterRefs, witness)
   for cluster in clusterRefs:
      if len(vscs.GetWitnessHosts(cluster)) != 1:
         msg = "ERROR: cluster %s is not a robo cluster" % cluster.name
         sys.exit(msg)
   print("Replacing the old witness(es) with shared witness %s" \
         " for clusters: %s" % (witness.name,
         [cluster.name for cluster in clusterRefs]))
   spec = vim.vsan.VsanVcStretchedClusterConfigSpec(
      witnessHost = witness,
      clusters = [vim.cluster.VsanStretchedClusterConfig(
         cluster = cluster
      ) for cluster in clusterRefs]
   )
   replaceWitnessTask = vscs.ReplaceWitnessHostForClusters(spec)
   vsanapiutils.WaitForTasks([replaceWitnessTask], si)

def removeWitnessForClusters(si, vscs, witness, clusterRefs):
   totalTasks = []
   for cluster in clusterRefs:
      print("Removing witness %s from cluster %s" % \
            (witness.name, cluster.name))
      removeTask = vscs.RemoveWitnessHost(cluster, witness)
      totalTasks.append(vsanapiutils.ConvertVsanTaskToVcTask(
                        removeTask, si._stub))
   vsanapiutils.WaitForTasks(totalTasks, si)

def getWitnessClusters(si, vscs, witness):
   clusterNames = []
   getWitnessClustrs = vscs.QueryWitnessHostClusterInfo(witness)
   for cluster in getWitnessClustrs:
      clusterMo = vim.ClusterComputeResource(cluster.cluster._moId, si._stub)
      clusterNames.append(clusterMo.name)
   return clusterNames

class LogWitnessStatus(object):
   def __init__(self, si, vscs, witness):
      self.si = si
      self.vscs = vscs
      self.witness = witness

   def __enter__(self):
      print("Before Ops: shared witness %s has joined the following clusters:"
            " %s" % (self.witness.name,
            getWitnessClusters(self.si, self.vscs, self.witness)))

   def __exit__(self, *a):
      print("After Ops: Now shared witness %s has joined the following"
            " clusters: %s" % (self.witness.name,
            getWitnessClusters(self.si, self.vscs, self.witness)))

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

   if aboutInfo.apiType == 'VirtualCenter':
      majorApiVersion = aboutInfo.apiVersion
      if LooseVersion(majorApiVersion) < LooseVersion('7.0.1'):
         msg = "The Virtual Center with version %s (lower than 7.0U1) is not "\
               "supported." % aboutInfo.apiVersion
         sys.exit(msg)
      # Get vSAN health system from the vCenter Managed Object references.
      vcMos = vsanapiutils.GetVsanVcMos(
            si._stub, context=context, version=apiVersion)
      vscs = vcMos['vsan-stretched-cluster-system']

      witness = getComputeInstance(args.witness, si)
      if not witness:
         msg = 'Given witness host %s is not found in %s' % \
               (args.witness, args.vc)
         sys.exit(msg)
      witness = witness.host[0]
      allClusters= []
      if args.roboClusters:
         roboClusters = [clusterName.strip() for clusterName \
                         in args.roboClusters.split(',')]
         roboClusters = getClusterInstances(roboClusters, si)
         allClusters.extend(roboClusters)
         with LogWitnessStatus(si, vscs, witness):
            replaceWitnessInBatch(si, vscs, witness, roboClusters)

      if args.normalClusters:
         twoNodesClusters = [clusterName.strip() for clusterName \
                             in args.normalClusters.split(',')]
         twoNodesClusters = getClusterInstances(twoNodesClusters, si)
         allClusters.extend(twoNodesClusters)
         with LogWitnessStatus(si, vscs, witness):
            convertToRoboClusterInBatch(si, vscs, witness, twoNodesClusters)

      with LogWitnessStatus(si, vscs, witness):
         removeWitnessForClusters(si, vscs, witness, allClusters)
   else:
      print('Remote host should be a Virtual Center ')
      return -1

if __name__ == "__main__":
   main()
