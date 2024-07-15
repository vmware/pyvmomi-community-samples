#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2019-2024 Broadcom. All Rights Reserved.
Broadcom Confidential. The term "Broadcom" refers to Broadcom Inc.

This file includes sample code for vCenter to call 2 vSAN APIs
for resource check for EMM (Enter Maintenance Mode): "PerformResourceCheck" and
"GetResourceCheckStatus".

To provide an example of vCenter vSAN API access, it calls
"PerformResourceCheck" with "ensureObjectAccessibility" option first and then
calls "GetResourceCheckStatus" to determine the what-if Dcom3.0 stauts on the
cluster.

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

def getClusterInstance(clusterName, serviceInstance):
   content = serviceInstance.RetrieveContent()
   searchIndex = content.searchIndex
   datacenters = content.rootFolder.childEntity
   for datacenter in datacenters:
      cluster = searchIndex.FindChild(datacenter.hostFolder, clusterName)
      if cluster is not None:
         return cluster
   return None

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

      cluster = getClusterInstance(args.clusterName, si)
      if cluster is None:
         print("Cluster %s is not found for %s", args.clusterName, args.host)
         return -1

      hosts=cluster.host
      if len(hosts) < 1:
         print("The cluster has no host in there. Please add atleast 1 host" +
               " and try again.")
         return -1

      firstHost=hosts[0]

      # Get vSAN health system from the vCenter Managed Object references.
      vcMos = vsanapiutils.GetVsanVcMos(
            si._stub, context=context, version=apiVersion)
      vscrcs = vcMos['vsan-cluster-resource-check-system']

      mSpec = vim.host.MaintenanceSpec(
                 vsanMode = vim.vsan.host.DecommissionMode(
                               objectAction = "ensureObjectAccessibility"))
      hostUuid = firstHost.configManager.vsanSystem.config.clusterInfo.nodeUuid
      spec = vim.vsan.ResourceCheckSpec(operation="EnterMaintenanceMode",
                                        entities=[hostUuid],
                                        maintenanceSpec=mSpec)
      tsk = vscrcs.PerformResourceCheck(spec, cluster)
      tsk = vim.Task(tsk._moId, cluster._stub)
      task.WaitForTask(tsk)
      resRes = vscrcs.GetResourceCheckStatus(spec, cluster)

      # Both resource check compelted and result is green.
      if (resRes.status.lower() == "resourcecheckcompleted") and \
         (resRes.result.status.lower() == "green"):
         print("EMM will proceed successfully.")
      else:
         print("EMM will NOT be successful. %s and it is %s"
               %(resRes.status, resRes.result.status))

if __name__ == "__main__":
   main()
