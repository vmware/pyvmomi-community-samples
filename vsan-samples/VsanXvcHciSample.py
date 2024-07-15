#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2022-2024 Broadcom. All Rights Reserved.
Broadcom Confidential. The term "Broadcom" refers to Broadcom Inc.

This file includes sample codes for the xvc HCI API:
1. PrecheckDatastoreSource
2. CreateDatastoreSource
3. DestroyDatastoreSource
4. QueryHciMeshDatastores
5. mount the cluster to a remote server cluster
6. unmount the cluster from a remote server cluster

"""

__author__ = 'Broadcom, Inc'
import sys
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, VmomiSupport
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
       description='Process args for xvc hcimesh')
   parser.add_argument('-cip', '--clientIp', required=True, action='store',
                       help='IP of the client.')
   parser.add_argument('-cc', '--clientCluster', required=True, action='store',
                       help='Name of the client cluster.')
   parser.add_argument('-cdc', '--clientDatacenter', required=True,
                       action='store',
                       help='Name of the client Datacenter.')
   parser.add_argument('-sip', '--serverIp', required=True, action='store',
                       help='IP of the server to be mounted.')
   parser.add_argument('-sc', '--serverCluster', required=True, action='store',
                       help='Name of the server cluster to be mounted.')
   parser.add_argument('-sdc', '--serverDatacenter', required=True,
                       action='store',
                       help='Name of the server datacenter to be mounted.')
   parser.add_argument('-sds', '--serverDatastore', required=True,
                       action='store',
                       help='Name of the server datastore to be mounted.')
   parser.add_argument('-u', '--user', required=True, action='store',
                       help='User name to use when connecting to host')
   parser.add_argument('-p', '--password', required=True, action='store',
                       help='Password to use when connecting to host')
   args = parser.parse_args()
   return args

def GetSiAndMos(args, context, host, port=443):
   si = SmartConnect(host=host,
                     user=args.user,
                     pwd=args.password,
                     port=port,
                     sslContext=context)

   atexit.register(Disconnect, si)

   # Detecting whether the server host is vCenter or ESXi.
   aboutInfo = si.content.about
   apiVersion = vsanapiutils.GetLatestVmodlVersion(host, port)
   if aboutInfo.apiType != 'VirtualCenter':
      print("The XVC HCI APIs are only available on vCenter")
      exit(1)

   # Get vSAN remote datastore system from the vCenter Managed
   # Object references.
   vcMos = vsanapiutils.GetVsanVcMos(
         si._stub, context=context, version=apiVersion)
   return si, vcMos

def getClusterInstance(clusterName, datacenterName, serviceInstance):
   content = serviceInstance.RetrieveContent()
   searchIndex = content.searchIndex
   datacenters = content.rootFolder.childEntity
   for datacenter in datacenters:
      if datacenterName == datacenter.name:
         cluster = searchIndex.FindChild(datacenter.hostFolder, clusterName)
         if cluster is not None:
            return cluster
   return None

def getClusterInstanceHelper(clusterName, datacenterName, si, host):
   if clusterName:
      clusterInstance = getClusterInstance(clusterName, datacenterName, si)
      if clusterInstance is None:
         print("Cluster %s is not found for %s" % (clusterName, host))
         return None
   else:
      print('Server or Client cluster name argument is not provided')
      return None
   return clusterInstance

def getDatastoreInstance(cluster, datastoreName):
   for ds in cluster.datastore:
      if ds.summary.type == 'vsan' and \
         ds.summary.name == datastoreName:
         return ds
   print("The datastore %s couldn't be found for cluster %s" % \
            (datastoreName, cluster.name))
   return None

def VerifyPrecheckResult(result, checkTargetName):
   abnormalItems = []
   for precheckItem in result.result:
      if precheckItem.status != "green":
         abnormalItems.append(precheckItem)
   if abnormalItems:
      print('Abnormal result found prechecking %s: %s' % abnormalItems)
      return -1

# Query remote vCenter information BEFORE adding it as a Datastore Source
def QueryHciMeshDs(args, clientSi, vcMos):
   # QueryHciMeshDatastores API
   vrds = vcMos['vsan-remote-datastore-system']
   cert = None
   # Invoke PrecheckDatastoreSource without specify a valid cert
   try:
      vrds.CreateDatastoreSource(vim.vsan.HciMeshDatastoreSource(
            vcInfo=vim.vsan.RemoteVcInfoStandalone(
                      linkType='standalone',
                      vcHost=args.serverIp,
                      user=args.user,
                      password=args.password)))
   except vim.fault.VsanSslVerifyCertFault as e:
      cert = e.cert
      print('CreateDatastoreSource for %s: Got SSL verify fault: %s' %
            (args.serverIp, cert))

   querySpecs = [vim.vsan.XvcQuerySpec(objectModel='datastore'),
                    vim.vsan.XvcQuerySpec(objectModel='providerVcenter'),
                    vim.vsan.XvcQuerySpec(objectModel='clientVcenter'),
                    vim.vsan.XvcQuerySpec(objectModel='clientCluster')]
   remoteVcInfos = [vim.vsan.RemoteVcInfoStandalone(
                          linkType='standalone',
                          vcHost=args.serverIp,
                          user=args.user,
                          password=args.password,
                          cert=cert)]
   results = vrds.QueryHciMeshDatastores(querySpecs, remoteVcInfos)
   print('Query everything of %s before create Datastore Source: %s' %
                    (args.serverIp, results))

def PrecheckAndCreateDatastoreSource(args, clientSi, vcMos):
   vrds = vcMos['vsan-remote-datastore-system']
   cert = None

   # Invoke PrecheckDatastoreSource without specify a valid cert
   try:
      vrds.PrecheckDatastoreSource(vim.vsan.HciMeshDatastoreSource(
            vcInfo=vim.vsan.RemoteVcInfoStandalone(
                      linkType='standalone',
                      vcHost=args.serverIp,
                      user=args.user,
                      password=args.password)))
   except vim.fault.VsanSslVerifyCertFault as e:
      cert = e.cert
      print(
         'PrecheckDatastoreSource for %s: Got SSL verify fault: %s' %
         (args.serverIp, cert))

   # Invoke CreateDatastoreSource without specify a valid cert
   try:
      vrds.CreateDatastoreSource(vim.vsan.HciMeshDatastoreSource(
            vcInfo=vim.vsan.RemoteVcInfoStandalone(
                      linkType='standalone',
                      vcHost=args.serverIp,
                      user=args.user,
                      password=args.password)))
   except vim.fault.VsanSslVerifyCertFault as e:
      cert = e.cert
      print(
         'CreateDatastoreSource for %s: Got SSL verify fault: %s' %
         (args.serverIp, cert))

   # call PrecheckDatastoreSource with a valid cert
   results=vrds.PrecheckDatastoreSource(vim.vsan.HciMeshDatastoreSource(
           vcInfo=vim.vsan.RemoteVcInfoStandalone(
                     linkType='standalone', vcHost=args.serverIp,
                     user=args.user, password=args.password,
                     cert=cert)), operation="checkCreateDs")
   print('PrecheckDatastoreSource for %s: %s' %
                    (args.serverIp, results))
   VerifyPrecheckResult(results, args.serverIp)

   # call CreateDatastoreSource with a valid cert
   task = vrds.CreateDatastoreSource(vim.vsan.HciMeshDatastoreSource(
                vcInfo=vim.vsan.RemoteVcInfoStandalone(
                          linkType='standalone', vcHost=args.serverIp,
                          user=args.user,
                          password=args.password,
                          cert=cert)))
   task = vim.Task(task._moId, clientSi._stub)
   vsanapiutils.WaitForTasks([task], clientSi)
   if task.info.state != 'success':
      print('Failed to create datastore source with error: %s'
            % task.info.error)
      return -1
   print('Successfully create datastore source.')

def QueryDs(args, vcMos):
   vrds = vcMos['vsan-remote-datastore-system']
   results = vrds.QueryDatastoreSource()
   print('QueryDatastoreSource: %s' % results)
   assert(len(results) == 1 and
          results[0].vcInfo.vcHost == args.serverIp)

def MountUnmountCluster(args, clientSi, clientMos, clientCluster, serverDs):
   vccs = clientMos['vsan-cluster-config-system']
   csConfig = vccs.GetConfigInfoEx(clientCluster)
   xvcDatastores = getattr(csConfig.xvcDatastoreConfig, 'xvcDatastores',
                              None)
   if not xvcDatastores:
      xvcDatastores = []

   # The newly mounting remote vCenter datastore
   xvcDatastores.append(vim.vsan.XVCDatastoreInfo(
                           datastore = serverDs,
                           ownerVc = args.serverIp))

   # Mount a remote vCenter datastore
   xvcDatastoreConfig = vim.vsan.XVCDatastoreConfig(
                              xvcDatastores = xvcDatastores)
   spec = vim.vsan.ReconfigSpec(xvcDatastoreConfig=xvcDatastoreConfig)
   vsanTask = vccs.ReconfigureEx(clientCluster, spec)
   vcTask = vsanapiutils.ConvertVsanTaskToVcTask(vsanTask, clientSi._stub)
   vsanapiutils.WaitForTasks([vcTask], clientSi)
   if vcTask.info.state != 'success':
      print('Failed to mount remote datastore with error: %s'
            % vcTask.info.error)
      return -1
   print('Successfully mounted remote vSAN datastore %s on cluster %s'
          % (serverDs.name, clientCluster.name))

   # Test unmount
   xvcDatastoreConfig = vim.vsan.XVCDatastoreConfig(
                           xvcDatastores = [])
   spec = vim.vsan.ReconfigSpec(xvcDatastoreConfig=xvcDatastoreConfig)
   vsanTask = vccs.ReconfigureEx(clientCluster, spec)
   vcTask = vsanapiutils.ConvertVsanTaskToVcTask(vsanTask, clientSi._stub)
   vsanapiutils.WaitForTasks([vcTask], clientSi)
   if vcTask.info.state != 'success':
      print('Failed to unmount remote datastore with error: %s'
            % vcTask.info.error)
      return -1
   print('Successfully unmounted remote vSAN datastore %s on cluster %s'
          % (serverDs.name, clientCluster.name))

def DestroyDs(args, clientSi, clientMos):
   vrds = clientMos['vsan-remote-datastore-system']
   # Test DestoryDatastoreSource
   results=vrds.PrecheckDatastoreSource(vim.vsan.HciMeshDatastoreSource(
                 vcInfo=vim.vsan.RemoteVcInfoStandalone(
                    linkType='standalone', vcHost=args.serverIp,
                    user=args.user,password=args.password)),
                    operation="checkDestroyDs")
   print('PrecheckDatastoreSource for %s: %s' %
                    (args.serverIp, results))
   VerifyPrecheckResult(results, args.serverIp)

   task = vrds.DestroyDatastoreSource(
            vim.vsan.HciMeshDatastoreSource(
            vcInfo=vim.vsan.RemoteVcInfoStandalone(
                  linkType='standalone', vcHost=args.serverIp,
                  user=args.user,password=args.password)))
   task = vim.Task(task._moId, clientSi._stub)
   vsanapiutils.WaitForTasks([task], clientSi)
   if task.info.state != 'success':
      print('Failed to destory datastore source with error: %s'
            % task.info.error)
      return -1
   print('Successfully destory datastore source')

def main():
   args = GetArgs()

   # For python 2.7.9 and later, the default SSL context has more strict
   # connection handshaking rule. We may need turn off the hostname checking
   # and client side cert verification.
   context = None
   if sys.version_info[:3] > (2,7,8):
      context = ssl.create_default_context()
      context.check_hostname = False
      context.verify_mode = ssl.CERT_NONE

   # Get client and server cluster and datastore instances
   clientSi, clientMos = GetSiAndMos(args, context, args.clientIp)
   clientCluster = getClusterInstanceHelper(args.clientCluster,
                                            args.clientDatacenter,
                                            clientSi, args.clientIp)

   serverSi, serverMos = GetSiAndMos(args, context, args.serverIp)
   serverCluster = getClusterInstanceHelper(args.serverCluster,
                                            args.serverDatacenter,
                                            serverSi, args.serverIp)
   serverDs = getDatastoreInstance(serverCluster, args.serverDatastore)
   if serverDs is None:
      return -1

   QueryHciMeshDs(args, clientSi, clientMos)
   PrecheckAndCreateDatastoreSource(args, clientSi, clientMos)
   QueryDs(args, clientMos)
   MountUnmountCluster(args, clientSi, clientMos, clientCluster, serverDs)
   DestroyDs(args, clientSi, clientMos)

if __name__ == "__main__":
   main()
