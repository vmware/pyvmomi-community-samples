#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2016-2024 Broadcom. All Rights Reserved.
The term "Broadcom" refers to Broadcom Inc. and/or its subsidiaries.

This file includes sample code for vCenter vSAN API accessing.

To provide an example of vCenter side vSAN API access, it shows how to run
Mount Precheck, Mount and Unmount a remote vSAN datastore using
VsanRemoteDatastoreSystem MO and check the health summary.

"""

__author__ = 'Broadcom, Inc'

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
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
   parser.add_argument('--servercluster', dest='serverClusterName',
                       metavar="CLUSTER")
   parser.add_argument('--clientcluster', dest='clientClusterName',
                       metavar="CLUSTER")
   args = parser.parse_args()
   return args

def getClusterInstance(clusterName, serviceInstance):
   content = serviceInstance.RetrieveContent()
   searchIndex = content.searchIndex
   datacenters = content.rootFolder.childEntity
   for datacenter in datacenters:
      cluster = searchIndex.FindChild(datacenter.hostFolder, clusterName)
      if cluster is not None:
         return cluster
   return None

def getRemoteDatastores(clusterRef):
   """
   Get remote vsan datastore with cluster instance
   @param clusterRef Given cluster reference
   @return dsList Vsan datastores
   """
   # Get vsan datastore
   dsList = [ds for ds in clusterRef.datastore if ds.summary.type == 'vsan']
   if len(dsList) == 0:
      print("ERROR: No vSAN datastore found")
      return None
   return dsList

def verifyPrecheckFailedResult(result):
   """
   For checking the MountPrecheck failed result in detail
   E.g. Some connectivity issue in a cluster Like, cluster partition, etc.
   Red: Indicates severe warnings
   Yellow: Indicates light warnings
   Green: Indicates no warnings
   """
   status = True
   for precheckItem in result.result:
      if precheckItem.status == "red":
         print('Precheck Item failed: %s' % precheckItem.type)
         print(precheckItem.reason)
         status = False
   return status

def getClusterInstanceHelper(clusterName, si, host):
   if clusterName:
      clusterInstance = getClusterInstance(clusterName, si)
      if clusterInstance is None:
         print("Cluster %s is not found for %s" % (clusterName, host))
         return None
   else:
      print('Server or Client cluster name argument is not provided')
      return None
   return clusterInstance

def mountUnmountDatastore(si, vsccs, cluster, dsList, vsanConfig, dsConfig):
   spec = vim.vsan.ReconfigSpec(vsanClusterConfig=vsanConfig,
                                datastoreConfig=dsConfig)
   vsanTask = vsccs.ReconfigureEx(cluster, spec)
   vcTask = vsanapiutils.ConvertVsanTaskToVcTask(vsanTask, si._stub)
   vsanapiutils.WaitForTasks([vcTask], si)
   if vcTask.info.state != 'success':
      print('Failed to (un)mount remote datastore with error: %s'
            % vcTask.info.error)
      return -1
   print('Successfully (un)mounted remote vSAN datastore %s on cluster %s'
          % (dsList[0].name, cluster.name))

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

      # Get vSAN remote datastore system from the vCenter Managed
      # Object references.
      vcMos = vsanapiutils.GetVsanVcMos(
            si._stub, context=context, version=apiVersion)
      vrds = vcMos['vsan-remote-datastore-system']
      # Get non-vSAN client cluster instance
      clientCluster = getClusterInstanceHelper(args.clientClusterName,
                                               si, args.host)
      # Get vSAN server cluster instance
      serverCluster = getClusterInstanceHelper(args.serverClusterName,
                                               si, args.host)
      if serverCluster is None or clientCluster is None:
         return -1

      # Make the 'client' - non-vSAN cluster as Compute mode
      vccs = vcMos['vsan-cluster-config-system']
      vccs.GetConfigInfoEx(clientCluster)
      rs = vim.vsan.ReconfigSpec(mode=vim.vsan.Mode.Mode_Compute)
      tsk = vccs.ReconfigureEx(clientCluster, rs)
      tsk = vim.Task(tsk._moId, clientCluster._stub)
      vsanapiutils.WaitForTasks([tsk], si)
      print (tsk.info)

      """
      Mount/Unmount work with desired state mechanism. Spec needs to contain the
      list of existing remote datastores. For a given spec:
      Mount: Provided remote vSAN datastore(s) will be mounted to target
             vSAN/Compute mode cluster, skip if already mounted
      Unmount: All in use remote vSAN datastores of target vSAN/Compute mode cluster
               will be unmounted if not specified in desired spec.
      """

      # Get remote datastore list from the server cluster
      vsanDatastore = getRemoteDatastores(serverCluster)

      # Run MountPrecheck API and verify the result for failures
      if vsanDatastore is not None:
         remoteVsanDatastore = vsanDatastore[0]
         print('Running MountPrecheck on cluster: %s' % clientCluster.name)
         result = vrds.MountPrecheck(clientCluster, remoteVsanDatastore)
         if verifyPrecheckFailedResult(result):
         # if True:
            vsccs = vcMos['vsan-cluster-config-system']
            vsanConfig = vim.vsan.cluster.ConfigInfo(enabled=None)

            # Mounting a remote datastore
            print('Mounting remote datastore on cluster: %s'
                   % clientCluster.name)
            dsConfig = vim.vsan.AdvancedDatastoreConfig(
                          remoteDatastores=vsanDatastore)
            mountUnmountDatastore(si, vsccs, clientCluster, vsanDatastore,
                                  vsanConfig, dsConfig)

            # Checking health summary of the compute cluster
            chs = vcMos['vsan-cluster-health-system']
            health = chs.VsanQueryVcClusterHealthSummary(clientCluster)
            print('Health summary of compute cluster %s: %s' % (clientCluster, health))

            # Unmounting a remote datastore
            print('Unmounting remote datastore from cluster: %s'
                  % clientCluster.name)
            dsConfig = vim.vsan.AdvancedDatastoreConfig(remoteDatastores=[])
            mountUnmountDatastore(si, vsccs, clientCluster, vsanDatastore,
                                  vsanConfig, dsConfig)
   else:
      print('Host provided should be a Virtual Center')
      return -1

if __name__ == "__main__":
   main()
