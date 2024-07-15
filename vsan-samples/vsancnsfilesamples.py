#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2019-2024 Broadcom. All Rights Reserved.
The term "Broadcom" refers to Broadcom Inc. and/or its subsidiaries.

This file includes sample code for managing file volume using the vSAN
Cloud Native Storage API.

To provide an example of vSAN CNS API access, it shows how to create
CNS file volume, query CNS file volume, update file volume metadata,
together with delete CNS file volume.

NOTE: using vSAN CNS API for file volume requires a minimal
vsan.version.version12 Stub.

"""

__author__ = 'Broadcom, Inc'
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, pbm, VmomiSupport, SoapStubAdapter
import sys
import ssl
import atexit
import argparse

# Import the vSAN API python bindings
import vsanapiutils

# Users can customize the parameters according to your own environment
DOMAIN_NAME = "VSANFS-PA.PRV"
IP_FQDN_DIC = {"192.168.111.2": "h192-168-111-2.example.com",
               "192.168.111.3": "h192-168-111-3.example.com",
               "192.168.111.4": "h192-168-111-4.example.com",
               "192.168.111.5": "h192-168-111-5.example.com"}
SUBNET_MASK = "255.255.255.0"
GATEWAY_ADDRESS = "192.168.111.1"
DNS_SUFFIXES = ["example.com"]
DNS_ADDRESS = ["1.2.3.4"]

def GetArgs():
   """
   Supports the command-line arguments listed below.
   """
   parser = argparse.ArgumentParser(
       description='Process args for vSAN file service sample application')
   parser.add_argument('-s', '--host', required=True, action='store',
                       help='Remote host to connect to')
   parser.add_argument('-o', '--port', type=int, default=443, action='store',
                       help='Port to connect on')
   parser.add_argument('-u', '--user', required=True, action='store',
                       help='User name to use when connecting to host')
   parser.add_argument('-p', '--password', required=True, action='store',
                       help='Password to use when connecting to host')
   parser.add_argument('--cluster', dest='clusterName', metavar="CLUSTER",
                       default='VSAN-Cluster')
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

def getVsanDatastore(clusterName, serviceInstance):
   """
   Get vsan datastore with cluster instance
   @param clusterName Given cluster name
   @param vcServiceInst Vc service instance
   @return dsList Vsan datastores
   """
   # Get cluster reference
   content = serviceInstance.RetrieveContent()
   searchIndex = content.searchIndex
   datacenters = content.rootFolder.childEntity
   clusterRef = None
   for datacenter in datacenters:
      cluster = searchIndex.FindChild(datacenter.hostFolder, clusterName)
      if cluster is not None:
         clusterRef = cluster
         break
   if clusterRef is None:
      print("ERROR: Cluster {0} is not found".format(clusterName))
      return None

   # Get vsan datastore
   dsList = [ds for ds in clusterRef.datastore if ds.summary.type == 'vsan']
   if len(dsList) == 0:
      print("ERROR: No vSAN datastore found")
      return None
   return dsList

def getFileServiceDomainConfig():
   networkProfiles = []
   for ipAddress, fqdn in IP_FQDN_DIC.items():
      networkProfile = vim.vsan.FileServiceIpConfig(
            dhcp=False, ipAddress=ipAddress, subnetMask=SUBNET_MASK,
            gateway=GATEWAY_ADDRESS, fqdn=fqdn)
      networkProfiles.append(networkProfile)
   networkProfiles[0].isPrimary = True

   fileServiceDomainConfig = vim.vsan.FileServiceDomainConfig(
         name = DOMAIN_NAME,
         dnsServerAddresses = DNS_ADDRESS,
         dnsSuffixes = DNS_SUFFIXES,
         fileServerIpConfig = networkProfiles)

   return fileServiceDomainConfig

def prepareFileVolumeCreateSpec(args, volumeName, datastores=None):
   """
   Creates file volume createSpec for create api
   @param args
   @param volumeName Volume name
   @param datastores Array of datastore
   @return createSpec Specifications for volumes to be created
   """
   clusterId1 = "k8_cls_1"
   podEntityType = "POD"
   pvcEntityType = "PERSISTENT_VOLUME_CLAIM"
   pvEntityType = "PERSISTENT_VOLUME"
   podEntityName1 = "test-pod1"
   pvcEntityName1 = "test-pvc1"
   pvEntityName1 = "test-pv1"
   nameSpace = "default"
   pvcLabels1 = [vim.KeyValue(key="PVCkey1", value="PVCvalue1")]
   pvLabels1 = [vim.KeyValue(key="PVkey1", value="PVvalue1")]

   containerCluster = vim.cns.ContainerCluster()
   containerCluster.clusterType = "KUBERNETES"
   containerCluster.clusterId = clusterId1
   containerCluster.vSphereUser = args.user

   backingOption = vim.cns.VsanFileShareBackingDetails()
   backingOption.capacityInMb = 1024L
   createSpec = vim.cns.VolumeCreateSpec()
   createSpec.name = volumeName
   createSpec.volumeType = "FILE"

   netPermission = [vim.vsan.FileShareNetPermission(
      ips='*',
      permissions=vim.vsan.FileShareAccessType.READ_WRITE,
      allowRoot=True)]
   cnsFileCreateSpec = vim.cns.VSANFileCreateSpec()
   cnsFileCreateSpec.softQuotaInMb = 100L
   cnsFileCreateSpec.permission = netPermission
   createSpec.createSpec = cnsFileCreateSpec

   referredEntityToPVC1 = vim.cns.KubernetesEntityReference()
   referredEntityToPVC1.entityType = pvcEntityType
   referredEntityToPVC1.entityName = pvcEntityName1
   referredEntityToPVC1.namespace = nameSpace
   referredEntityToPVC1.clusterId = clusterId1
   referredEntityToPV1 = vim.cns.KubernetesEntityReference()
   referredEntityToPV1.entityType = pvEntityType
   referredEntityToPV1.entityName = pvEntityName1
   referredEntityToPV1.clusterId = clusterId1
   podMetaData1 = prepareK8sEntityMetaData(
      entityName=podEntityName1, clusterId=clusterId1,
      namespace=nameSpace,
      entityType=podEntityType,
      referredEntity=[referredEntityToPVC1])
   pvcMetaData1 = prepareK8sEntityMetaData(
      entityName=pvcEntityName1, clusterId=clusterId1,
      namespace=nameSpace,
      entityType=pvcEntityType, labelkv=pvcLabels1,
      referredEntity=[referredEntityToPV1])
   pvMetaData1 = prepareK8sEntityMetaData(
      entityName=pvEntityName1, clusterId=clusterId1,
      entityType=pvEntityType, labelkv=pvLabels1)
   metadata = vim.cns.VolumeMetadata()
   metadata.containerCluster = containerCluster
   metadata.containerClusterArray = [containerCluster]
   metadata.entityMetadata = [podMetaData1, pvcMetaData1, pvMetaData1]

   createSpec.metadata = metadata
   createSpec.backingObjectDetails = backingOption
   createSpec.datastores = []
   if datastores:
      createSpec.datastores.extend(datastores)

   createSpecs = []
   createSpecs.append(createSpec)
   return createSpecs

def prepareFileVolumeMetadataUpdateSpec(args, volumeId):

   """
   Creates file volume updateSpec for create api
   @param args
   @param volumeId Volume Id
   @return updateSpec Specifications for volumes to be updated
   """
   clusterId1 = "k8_cls_1"
   clusterId2 = "k8_cls_2"
   nameSpace = "default"
   clusterType = "KUBERNETES"
   podEntityType = "POD"
   pvcEntityType = "PERSISTENT_VOLUME_CLAIM"
   pvEntityType = "PERSISTENT_VOLUME"
   podEntityName1 = "test-pod1"
   podEntityName2 = "test-pod2"
   pvcEntityName1 = "test-pvc1"
   pvcEntityName2 = "test-pvc2"
   pvEntityName1 = "test-pv1"
   pvcLabels1 = [vim.KeyValue(key="PVCkey1", value="PVCvalue1")]
   pvcLabels2 = [vim.KeyValue(key="PVCkey2", value="PVCvalue2")]
   pvLabels1 = [vim.KeyValue(key="PVkey1", value="PVvalue1")]

   updateSpec = vim.cns.VolumeMetadataUpdateSpec()
   updateSpec.volumeId = volumeId
   metadata = vim.cns.VolumeMetadata()

   containerCluster1 = vim.cns.ContainerCluster()
   containerCluster1.clusterType = clusterType
   containerCluster1.clusterId = clusterId1
   containerCluster1.vSphereUser = args.user
   containerCluster2 = vim.cns.ContainerCluster()
   containerCluster2.clusterType = clusterType
   containerCluster2.clusterId = clusterId2
   containerCluster2.vSphereUser = args.user
   metadata.containerCluster = containerCluster1
   metadata.containerClusterArray = [containerCluster1, containerCluster2]

   referredEntityToPVC1 = vim.cns.KubernetesEntityReference()
   referredEntityToPVC1.entityType = pvcEntityType
   referredEntityToPVC1.entityName = pvcEntityName1
   referredEntityToPVC1.namespace = nameSpace
   referredEntityToPVC1.clusterId = clusterId1
   referredEntityToPVC2 = vim.cns.KubernetesEntityReference()
   referredEntityToPVC2.entityType = pvcEntityType
   referredEntityToPVC2.entityName = pvcEntityName2
   referredEntityToPVC2.namespace = nameSpace
   referredEntityToPVC2.clusterId = clusterId2
   referredEntityToPV1 = vim.cns.KubernetesEntityReference()
   referredEntityToPV1.entityType = pvEntityType
   referredEntityToPV1.entityName = pvEntityName1
   referredEntityToPV1.clusterId = clusterId1

   podMetaData1 = prepareK8sEntityMetaData(
      entityName=podEntityName1, clusterId=clusterId1,
      namespace=nameSpace,
      entityType=podEntityType,
      referredEntity=[referredEntityToPVC1])
   podMetaData2 = prepareK8sEntityMetaData(
      entityName=podEntityName2, clusterId=clusterId2,
      namespace=nameSpace,
      entityType=podEntityType,
      referredEntity=[referredEntityToPVC2])
   pvcMetaData1 = prepareK8sEntityMetaData(
      entityName=pvcEntityName1, clusterId=clusterId1,
      namespace=nameSpace,
      entityType=pvcEntityType, labelkv=pvcLabels1,
      referredEntity=[referredEntityToPV1])
   pvcMetaData2 = prepareK8sEntityMetaData(
      entityName=pvcEntityName2, clusterId=clusterId2,
      namespace=nameSpace,
      entityType=pvcEntityType, labelkv=pvcLabels2,
      referredEntity=[referredEntityToPV1])
   pvMetaData1 = prepareK8sEntityMetaData(
      entityName=pvEntityName1, clusterId=clusterId1,
      entityType=pvEntityType, labelkv=pvLabels1)

   metadata.entityMetadata = [podMetaData1, podMetaData2, pvcMetaData1,
                              pvcMetaData2, pvMetaData1]
   updateSpec.metadata = metadata
   updateSpecs = []
   updateSpecs.append(updateSpec)
   return updateSpecs

def prepareK8sEntityMetaData(entityName, entityType, namespace=None,
                             deleteFlag=None, labelkv=None,
                             clusterId=None, referredEntity=None):
   k8sEntityMetaData = vim.cns.KubernetesEntityMetadata()
   if namespace is not None:
      k8sEntityMetaData.namespace = namespace
   k8sEntityMetaData.entityType = entityType
   k8sEntityMetaData.entityName = entityName
   if clusterId is not None:
      k8sEntityMetaData.clusterId = clusterId
   if deleteFlag is None:
      k8sEntityMetaData.delete = False
   else:
      k8sEntityMetaData.delete = deleteFlag
   if labelkv is not None:
      k8sEntityMetaData.labels = labelkv
   if referredEntity is not None:
      k8sEntityMetaData.referredEntity = referredEntity
   return k8sEntityMetaData

def main():
   args = GetArgs()
   if args.password:
      password = args.password
   else:
      password = getpass.getpass(prompt='Enter password for VC %s and '
                                 'user %s: ' % (args.host, args.user))
   # For python 2.7.9 and later, the default SSL context has more strict
   # connection handshaking rule. We may need turn off the hostname
   # checking and client side cert verification.
   context = None
   if sys.version_info[:3] > (2,7,8):
      context = ssl.create_default_context()
      context.check_hostname = False
      context.verify_mode = ssl.CERT_NONE

   # Connect to vCenter, get vc service instance
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
      print("The vSAN file service APIs are only available on vCenter")
      return -1

   datastores = getVsanDatastore(args.clusterName, si)
   if datastores is None or len(datastores)==0:
      print("vsan datastore is not found for %s" % (args.host))
      return -1

   cluster = getClusterInstance(args.clusterName, si)
   if cluster is None:
      print("Cluster %s is not found for %s" % (args.clusterName, args.host))
      return -1

   vcMos = vsanapiutils.GetVsanVcMos(si._stub, context=context,
                                     version=apiVersion)
   vcfs = vcMos['vsan-cluster-file-service-system']
   vccs = vcMos['vsan-cluster-config-system']
   volmgr = vcMos['cns-volume-manager']

   # Find OVF download url
   print("Finding OVF download url ...")
   ovfUrl = vcfs.FindOvfDownloadUrl(cluster)
   if not ovfUrl:
      print("Failed to find the OVF download url.")
      return -1
   print("Found OVF download url: %s" % ovfUrl)

   # Download FSVM OVF files to vCenter
   print("Downloading ovf files from %s to vCenter ..." % ovfUrl)
   vsanTask = vcfs.DownloadFileServiceOvf(downloadUrl=ovfUrl)
   vcTask = vsanapiutils.ConvertVsanTaskToVcTask(vsanTask, si._stub)
   vsanapiutils.WaitForTasks([vcTask], si)
   if vcTask.info.state != 'success':
      print("Failed to download ovf files with error: %s"
            % vcTask.infor.error)
      return -1
   print("Downloaded ovf files to vCenter successfully")

   # Enable file service
   print("Enabling the file service")
   network = cluster.host[0].network[0]
   fileServiceConfig = vim.vsan.FileServiceConfig(
         enabled=True,
         network=network,
         domains=[],
   )
   clusterSpec = vim.vsan.ReconfigSpec(fileServiceConfig=fileServiceConfig)
   vsanTask = vccs.ReconfigureEx(cluster, clusterSpec)
   vcTask = vsanapiutils.ConvertVsanTaskToVcTask(vsanTask, si._stub)
   vsanapiutils.WaitForTasks([vcTask], si)
   if vcTask.info.state != 'success':
      print("Failed to enable file service with error: %s"
            % vcTask.info.error)
      return -1
   print("Enabled file service successfully")

   # Create file service domain
   fsDomainConfig = getFileServiceDomainConfig()
   domainName = fsDomainConfig.name
   print("Creating file service domain")
   vsanTask = vcfs.CreateFileServiceDomain(fsDomainConfig, cluster)
   vcTask = vsanapiutils.ConvertVsanTaskToVcTask(vsanTask, si._stub)
   vsanapiutils.WaitForTasks([vcTask], si)
   if vcTask.info.state != 'success':
      print("Failed to create file service domain with error: %s"
            % vcTask.info.error)
      return -1
   print("Created file service domain %s successfully"
         % domainName)

   # Create file volume
   volumeName = "file_volume_sdk_test"
   print("Creating file volume: %s" % volumeName)
   createSpecs = prepareFileVolumeCreateSpec(args,
                                             volumeName=volumeName,
                                             datastores=datastores)
   cnsCreateTask = volmgr.Create(createSpecs)
   vcTask = vsanapiutils.ConvertVsanTaskToVcTask(cnsCreateTask, si._stub)
   vsanapiutils.WaitForTasks([vcTask], si)
   print(('Create CNS file volume task finished with status: %s' %
          vcTask.info.state))
   if vcTask.info.error is not None:
      print("Create CNS file volume failed with error %s"
            % vcTask.info.error)
      return -1

   # Query CNS volume
   print("Querying file volume with volumeName: %s" % volumeName)
   filterSpec = vim.cns.QueryFilter()
   filterSpec.names = [volumeName]
   volumeQueryResult = volmgr.Query(filterSpec)
   print("CNS query result: {}".format(volumeQueryResult))
   if volumeQueryResult is None:
      print("ERROR: Query CNS volume failed, result is %s"
            % volumeQueryResult)
      return -1
   volumeId = volumeQueryResult.volumes[0].volumeId

   # Update volume metadata
   print("Updating file volume metadata with volumeId: %s" % volumeId.id)
   updateSpecs = prepareFileVolumeMetadataUpdateSpec(args, volumeId)
   cnsUpdateTask = volmgr.UpdateVolumeMetadata(updateSpecs)
   vcTask = vsanapiutils.ConvertVsanTaskToVcTask(cnsUpdateTask, si._stub)
   vsanapiutils.WaitForTasks([vcTask], si)
   print(('Update CNS file volume task finished with status: %s' %
          vcTask.info.state))
   if vcTask.info.error is not None:
      print("Update CNS file volume failed with error %s"
            % vcTask.info.error)
      return -1

   # Delete CNS volume
   print("Deleting file volume with volumeId: %s" % volumeId.id)
   cnsDeleteTask = volmgr.Delete([volumeId], deleteDisk=True)
   vcTask = vsanapiutils.ConvertVsanTaskToVcTask(cnsDeleteTask, si._stub)
   vsanapiutils.WaitForTasks([vcTask], si)
   print(('Delete CNS volume task finished with status: %s'
          % vcTask.info.state))
   if vcTask.info.error is not None:
      print("Delete CNS volume failed with error %s"
            % vcTask.info.error)
      return -1

   # Disable file service
   print("Disabling file service")
   fileServiceConfig = vim.vsan.FileServiceConfig(enabled=False)
   clusterSpec = vim.vsan.ReconfigSpec(fileServiceConfig=fileServiceConfig)
   vsanTask = vccs.ReconfigureEx(cluster, clusterSpec)
   vcTask = vsanapiutils.ConvertVsanTaskToVcTask(vsanTask, si._stub)
   vsanapiutils.WaitForTasks([vcTask], si)
   if vcTask.info.state != 'success':
      print("Failed to disable file service with error: %s"
            % vcTask.info.error)
      return -1
   print("Disabled file service successfully")


if __name__ == "__main__":
   main()
