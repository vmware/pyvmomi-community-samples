#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2019-2024 Broadcom. All Rights Reserved.
The term "Broadcom" refers to Broadcom Inc. and/or its subsidiaries.

This file includes sample code for the vSAN Cloud Native Storage API.

To provide an example of vSAN CNS API access, it shows how to create CNS volume,
query CNS volume, together with delete CNS volume.

NOTE: using vSAN CNS API requires a minimal vim.version.version11 Stub.

usage: vsancnssamples.py [-h] -s HOST [-o PORT] -u USER [-p PASSWORD] [--cluster CLUSTER]
  -h, --help            show this help message and exit
  -s HOST, --host HOST  Remote vCenter host to connect to
  -o PORT, --port PORT  Port to connect on
  -u USER, --user USER  User name to use when connecting to host
  -p PASSWORD, --password PASSWORD
                        Password to use when connecting to host
  --cluster CLUSTER

"""

__author__ = 'Broadcom, Inc'

import sys
import ssl
import atexit
import argparse
import getpass
import vsanapiutils

from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect

import pyVmomi
import vsanmgmtObjects

if sys.version[0] < '3':
   input = raw_input

def main():
   args = GetArgs()

   # Create connection and get vc service instance and CNS volume manager stub
   (vcServiceInst, cnsVolumeManager) = connectToServers(args)

   # Create CNS volume
   volumeName = "volume_sdk_test"
   datastores = GetVsanDatastore(args.clusterName, vcServiceInst)
   createSpecs = PrepareVolumeCreateSpec(args,
                                         volumeName=volumeName,
                                         datastores=datastores)
   cnsCreateTask = cnsVolumeManager.Create(createSpecs)
   vcTask = vsanapiutils.ConvertVsanTaskToVcTask(cnsCreateTask, vcServiceInst._stub)
   vsanapiutils.WaitForTasks([vcTask], vcServiceInst)
   print(('Create CNS volume task finished with status: %s' %
                 vcTask.info.state))
   if vcTask.info.error is not None:
      msg = "Create CNS volume failed with error '{0}'".format(vcTask.info.error)
      sys.exit(msg)

   # Query CNS volume
   filterSpec = vim.cns.QueryFilter()
   filterSpec.names = [volumeName]
   volumeQueryResult = cnsVolumeManager.Query(filterSpec)
   print("CNS query result: {}".format(volumeQueryResult))
   if volumeQueryResult is None:
      msg = "ERROR: Query CNS volume failed. result is \n {0}".format(volumeQueryResult)
      sys.exit(msg)
   volumeId = volumeQueryResult.volumes[0].volumeId

   # Delete CNS volume
   cnsDeleteTask = cnsVolumeManager.Delete([volumeId], deleteDisk=True)
   vcTask = vsanapiutils.ConvertVsanTaskToVcTask(cnsDeleteTask, vcServiceInst._stub)
   vsanapiutils.WaitForTasks([vcTask], vcServiceInst)
   print(('Delete CNS volume task finished with status: %s' %
                 vcTask.info.state))
   if vcTask.info.error is not None:
      msg = "Delete CNS volume failed with error '{0}'".format(vcTask.info.error)
      sys.exit(msg)

def GetArgs():
   """
   Supports the command-line arguments listed below.
   """
   parser = argparse.ArgumentParser(
       description='Process args for vSAN SDK sample application')
   parser.add_argument('-s', '--host', required=True, action='store',
                       help='Remote vCenter host to connect to')
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

def connectToServers(args):
   """
   Creates connections to the vCenter, vSAN and CNS volume manager
   @param args
   @return vc service instance, CNS volume manager stub
   """
   if args.password:
      password = args.password
   else:
      password = getpass.getpass(prompt='Enter password for host %s and '
                                        'user %s: ' % (args.host,args.user))

   # For python 2.7.9 and later, the default SSL context has stricter
   # connection handshaking rule, hence we are turning off the hostname checking
   # and client side cert verification.
   sslContext = None
   if sys.version_info[:3] > (2,7,8):
      sslContext = ssl.create_default_context()
      sslContext.check_hostname = False
      sslContext.verify_mode = ssl.CERT_NONE

   # Connect to vCenter, get vc service instance
   vcServiceInst = SmartConnect(host=args.host,
                                user=args.user,
                                pwd=password,
                                port=int(args.port),
                                sslContext=sslContext)
   atexit.register(Disconnect, vcServiceInst)

   # get vSAN service instance stub
   apiVersion = vsanapiutils.GetLatestVmodlVersion(args.host, int(args.port))
   vsanStub = vsanapiutils.GetVsanVcMos(vcServiceInst._stub,
                                     context = sslContext,
                                     version = apiVersion)

   # get CNS volume manager stub
   cnsVolumeManager = vsanStub['cns-volume-manager']

   return (vcServiceInst, cnsVolumeManager)

def GetVsanDatastore(clusterName, vcServiceInst):
   """
   Get vsan datastore with cluster instance
   @param clusterName Given cluster name
   @param vcServiceInst Vc service instance
   @return dsList Vsan datastores
   """
   # get cluster reference
   content = vcServiceInst.RetrieveContent()
   searchIndex = content.searchIndex
   datacenters = content.rootFolder.childEntity
   clusterRef = None
   for datacenter in datacenters:
      cluster = searchIndex.FindChild(datacenter.hostFolder, clusterName)
      if cluster is not None:
         clusterRef = cluster
         break
   if clusterRef is None:
      msg = "ERROR: Cluster {0} is not found".format(clusterName)
      sys.exit(msg)

   # get vsan datastore
   dsList = [ds for ds in clusterRef.datastore if ds.summary.type == 'vsan']
   if len(dsList) == 0:
      msg = "ERROR: No vSAN datastore found"
      sys.exit(msg)
   return dsList

def PrepareVolumeCreateSpec(args, volumeName, datastores=None):
   """
   Creates createSpec for create api
   @param args
   @param volumeName Volume name
   @param datastores Array of datastore
   @return createSpec Specifications for volumes to be created
   """
   containerCluster = vim.cns.ContainerCluster()
   containerCluster.clusterType = "KUBERNETES"
   containerCluster.clusterId = "k8_cls_1"
   containerCluster.vSphereUser = args.user
   backingOption = vim.cns.BlockBackingDetails()
   backingOption.capacityInMb = 1024L
   createSpec = vim.cns.VolumeCreateSpec()
   createSpec.name = volumeName
   createSpec.volumeType = "BLOCK"

   metadata = vim.cns.VolumeMetadata()
   metadata.containerCluster = containerCluster
   k8sEntityMetaData = vim.cns.KubernetesEntityMetadata()
   k8sEntityMetaData.namespace = "default"
   k8sEntityMetaData.entityType = "PERSISTENT_VOLUME_CLAIM"
   k8sEntityMetaData.entityName = "test-pvc"
   k8sEntityMetaData.delete = False
   metadata.entityMetadata = [k8sEntityMetaData]

   createSpec.metadata = metadata
   createSpec.backingObjectDetails = backingOption
   createSpec.datastores = []
   if datastores:
      createSpec.datastores.extend(datastores)

   createSpecs = []
   createSpecs.append(createSpec)
   return createSpecs

if __name__ == "__main__":
   main()
