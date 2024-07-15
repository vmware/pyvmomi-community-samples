#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2016-2024 Broadcom. All Rights Reserved.
The term "Broadcom" refers to Broadcom Inc. and/or its subsidiaries.

This file includes sample codes for vCenter vSAN resyncetaimprovement
API accessing.

To provide an example of vCenter side vSAN API access, it shows how to get resyc
query summary by  invoking the QuerySyncingVsanObjectsSummary() API of the
VsanVcObjectSystemImpl MO.

"""

__author__ = 'Broadcom, Inc'

from pyVim.connect import SmartConnect, Disconnect
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
from pyVmomi import vim, vmodl

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

def getClusterInstance(clusterName, serviceInstance):
   content = serviceInstance.RetrieveContent()
   searchIndex = content.searchIndex
   datacenters = content.rootFolder.childEntity
   for datacenter in datacenters:
      cluster = searchIndex.FindChild(datacenter.hostFolder, clusterName)
      if cluster is not None:
         return cluster
   return None

def displayResyncSummary(res):
   print('totalObjectsToSync = %s' % res.totalObjectsToSync)
   print('totalBytesToSync = %s' % res.totalBytesToSync)
   print('totalRecoveryETA = %s' % res.totalRecoveryETA)

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
      majorApiVersion = aboutInfo.apiVersion.split('.')[0]
      if int(majorApiVersion) < 6:
         print('The Virtual Center with version %s (lower than 6.0) is not '
               'supported.' % aboutInfo.apiVersion)
         return -1

      # Get vSAN reync query summary from the vCenter Managed Object references.
      vcMos = vsanapiutils.GetVsanVcMos(
            si._stub, context=context, version=apiVersion)
      vhs = vcMos['vsan-cluster-object-system']
      cluster = getClusterInstance(args.clusterName, si)

      if cluster is None:
         print("Cluster %s is not found for %s" % (args.clusterName, args.host))
         return -1

      of=vim.cluster.VsanSyncingObjectFilter()
      # Setting filter parameters for active objects.
      of.resyncStatus = 'active'
      of.resyncType = None
      of.offset = 0
      of.numberOfObjects = 100

      # Fetching resync summary from connected host in cluster.
      res=vhs.QuerySyncingVsanObjectsSummary(cluster,of)
      print('\nResync summary of active objects having any resync reason:')
      displayResyncSummary(res)

      # Setting filter parameters for active objects with
      # specific resync reason.
      of.resyncStatus = 'active'
      of.resyncType = 'evacuate'
      of.offset = 0
      of.numberOfObjects = 100

      # Fetching resync summary from connected host in cluster.
      res=vhs.QuerySyncingVsanObjectsSummary(cluster,of)
      print('\nResync summary of active objects having resync reason '
            'as evacuate:')
      displayResyncSummary(res)

      # Setting filter parameters for queued objects.
      of.resyncStatus = 'queued'
      of.resyncType = None
      of.offset = 0
      of.numberOfObjects = 100

      # Fetching resync summary from connected host in cluster.
      res=vhs.QuerySyncingVsanObjectsSummary(cluster,of)
      print('\nResync summary of queued objects having any resync reason:')
      displayResyncSummary(res)

      # Setting filter parameters for queued objects
      # with specific resync reason.
      of.resyncStatus = 'queued'
      of.resyncType = 'repair'
      of.offset = 0
      of.numberOfObjects = 100

      # Fetching resync summary from connected host in cluster.
      res=vhs.QuerySyncingVsanObjectsSummary(cluster,of)
      print('\nResync summary of queued objects having resync reason '
            'as repair:')
      displayResyncSummary(res)

if __name__ == "__main__":
   main()
