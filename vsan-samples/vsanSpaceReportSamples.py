#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2016-2024 Broadcom. All Rights Reserved.
Broadcom Confidential. The term "Broadcom" refers to Broadcom Inc.
and/or its subsidiaries.

This file includes sample codes for vCenter and ESXi sides vSAN space reporting
API QuerySpaceUsage accessing.

To provide an example of vSAN space reporting API access, it shows how to get
vSAN space usage result, including following types:
vSAN total capacity;
vSAN used capacity;
vSAN free capacity;
vSAN saved space by efficiency feature like deduplication or compression;
vSAN space usage break down by object type;
...

"""

__author__ = 'Broadcom, Inc'

import sys
import ssl
import atexit
import argparse
import getpass
if sys.version[0] < '3':
   input = raw_input
sys.path.append("/usr/lib64/vmware-vpx/vsan-health/")
sys.path.append("/usr/lib/vmware/site-packages/")
from pyVmomi import vim, VmomiSupport, pbm
import pyVim
from pyVim.connect import SmartConnect, Disconnect

# Import the vSAN API python bindings and utilities.
import pyVmomi
import vsanmgmtObjects
import vsanapiutils

def GetArgs():
   """
   Supports the command-line arguments listed below.
   """
   parser = argparse.ArgumentParser(
       description=
       'vSAN SDK sample application for vSAN space reporting API usage. '
       'It queries the space usage information for the specific cluster '
       'and print out the current space usage information, including total '
       'capacity usage overview, space efficiency status and capacity usage '
       'breakdown, etc.')
   parser.add_argument('-v', '--vc', required=True, action='store',
                       help='Remote vCenter Server to connect to')
   parser.add_argument('-o', '--port', type=int, default=443, action='store',
                       help='Port to connect on, default is 443')
   parser.add_argument('-u', '--user', required=True, action='store',
                       help='User name to use when connecting to '
                            'vCenter Server')
   parser.add_argument('-p', '--password', required=False, action='store',
                       help='Password to use when connecting to vCenter '
                            'Server. If not provided, it will prompt to '
                            'ask for manually inputting the password')
   parser.add_argument('--cluster', dest='clusterName', metavar="CLUSTER",
                      default='VSAN-Cluster',
                      help='The name of the vSAN cluster which the space usage '
                           'query is going to perform on')
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

def connectToServers(args, sslContext):
   """
   Creates connections to the vCenter, vSAN and vSAN space reporting system
   @param args
   @return vc service instance, cluster, vSAN space reporting system
   """
   if args.password:
      password = args.password
   else:
      password = getpass.getpass(prompt='Enter password for vc %s and '
                                        'user %s: ' % (args.vc, args.user))

   # Connect to vCenter, get vc service instance
   si = SmartConnect(host=args.vc,
                     user=args.user,
                     pwd=password,
                     port=int(args.port),
                     sslContext=sslContext)

   atexit.register(Disconnect, si)

   # Get vSAN service instance stub
   apiVersion = vsanapiutils.GetLatestVmodlVersion(args.vc, int(args.port))
   aboutInfo = si.content.about
   if aboutInfo.apiType != 'VirtualCenter':
      raise Exception("The sample script should be run against vc.")

   vsanStub = vsanapiutils.GetVsanVcMos(si._stub,
                                     context = sslContext,
                                     version = apiVersion)

   # Get vSAN cluster config system and vsan cluster health system
   vss = vsanStub['vsan-cluster-space-report-system']

   # Get cluster
   cluster = getClusterInstance(args.clusterName, si)

   return (si, cluster, vss)

def bytesToTibBytes(byteSize):
   tibSize = byteSize / (2**40)
   return round(tibSize, 4)

def main():
   args = GetArgs()

   # For python 2.7.9 and later, the default SSL context has stricter
   # connection handshaking rule, hence we are turning off the hostname checking
   # and client side cert verification.
   sslContext = None
   if sys.version_info[:3] > (2,7,8):
      sslContext = ssl.create_default_context()
      sslContext.check_hostname = False
      sslContext.verify_mode = ssl.CERT_NONE

   (si, cluster, vss) = connectToServers(args, sslContext)

   if cluster is None:
      print("Cluster %s is not found for %s" % (args.clusterName, args.vc))
      return -1
   else:
      # Here is an example of how to get space reporting results
      # by vSAN space reporting API.
      spaceResult = \
         vss.QuerySpaceUsage(cluster=cluster)

      if not spaceResult:
         print("Space result is None for the given cluster %s" % \
            args.clusterName)
         return -1

      print("vSAN Space Usage Overview")
      print("Total vSAN Capacity: "
            "%s TiB" % bytesToTibBytes(spaceResult.totalCapacityB))
      print("Used vSAN Capacity: "
            "%s TiB" % bytesToTibBytes(spaceResult.spaceOverview.usedB))
      print("Free vSAN Capacity: "
            "%s TiB" % bytesToTibBytes(spaceResult.freeCapacityB))

      if hasattr(spaceResult, 'efficientCapacity') and \
         spaceResult.efficientCapacity is not None:
         print("vSAN efficiency (Deduplication / Compression) is enabled")
         efficiencySavings = \
            spaceResult.efficientCapacity.logicalCapacityUsed - \
            spaceResult.efficientCapacity.physicalCapacityUsed
         print("Space saved by Efficiency: "
               "%s TiB" % bytesToTibBytes(efficiencySavings))

      if hasattr(spaceResult, 'spaceEfficiencyRatio') and \
         spaceResult.spaceEfficiencyRatio is not None:
         print("Space Efficiency Ratio: "
               "%sx" % spaceResult.spaceEfficiencyRatio.overallRatio)

      spaceUsageByObjectType = spaceResult.spaceDetail.spaceUsageByObjectType
      print("\nUsed Capacity Breakdown")
      print("vdisk: %s TiB" % bytesToTibBytes(sum([
         obj.usedB for obj in spaceUsageByObjectType
         if obj.objType == 'vdisk'
         ])))
      print("vmswap: %s TiB" % bytesToTibBytes(sum([
         obj.usedB for obj in spaceUsageByObjectType
         if obj.objType == 'vmswap'
         ])))
      print("statsdb: %s TiB" % bytesToTibBytes(sum([
         obj.usedB for obj in spaceUsageByObjectType
         if obj.objType == 'statsdb'
         ])))
      print("namespace: %s TiB" % bytesToTibBytes(sum([
         obj.usedB for obj in spaceUsageByObjectType
         if obj.objType == 'namespace'
         ])))
      print("traceobject: %s TiB" % bytesToTibBytes(sum([
         obj.usedB for obj in spaceUsageByObjectType
         if obj.objType == 'traceobject'
         ])))
      print("esaObjectOverhead: %s TiB" % bytesToTibBytes(sum([
         obj.usedB for obj in spaceUsageByObjectType
         if obj.objType == 'esaObjectOverhead'
         ])))
      print("fileSystemOverhead: %s TiB" % bytesToTibBytes(sum([
         obj.usedB for obj in spaceUsageByObjectType
         if obj.objType == 'fileSystemOverhead'
         ])))


if __name__ == "__main__":
   main()
