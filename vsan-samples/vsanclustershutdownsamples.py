#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2016-2024 Broadcom. All Rights Reserved.
The term "Broadcom" refers to Broadcom Inc. and/or its subsidiaries.

This file includes sample codes for vCenter and ESXi sides vSAN API accessing.

To provide an example of vCenter side vSAN API access, it shows how to get vSAN
cluster health status by invoking the QueryClusterHealthSummary() API of the
VsanVcClusterHealthSystem MO and check host connection by invoking the GetRuntimeStats()
API of the VsanVcClusterConfigSystem MO.

To provide an example of ESXi side vSAN API access, it shows how to power off/on cluster
by invoking the PerformClusterPowerAction() API of the VsanClusterPowerSystem MO.

"""

__author__ = 'Broadcom, Inc'

from pyVim.connect import SmartConnect, Disconnect
import sys
import ssl
import atexit
import argparse
import getpass
import json
if sys.version[0] < '3':
   input = raw_input

# Import the vSAN API python bindings and utilities.
import pyVmomi
import vsanmgmtObjects
import vsanapiutils
from pyVmomi import vim
import datetime
from datetime import timezone

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
   parser.add_argument('--poweraction', required=True, dest='powerAction',
                      action='store')
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


def precheckHealth(vchs, cluster):
   print("Start cluster shutdown precheck")
   healthData = vchs.QueryClusterHealthSummary(
       cluster, perspective="clusterPowerOffPrecheck")
   print("Start cluster shutdown precheck")
   if healthData:
      print("Overall health status:", healthData.overallHealth)
      if healthData.overallHealth == 'green':
         return True
      elif healthData.overallHealthDescription:
         print(healthData.overallHealthDescription)
   else:
      print("Failed to get health data.")
      return False
   # Check failed health tests
   if healthData.groups is None or len(healthData.groups) == 0:
      print("Groups are None")
      return False
   for group in healthData.groups:
      if group.groupHealth != 'green':
         for test in group.groupTests:
            if test.testHealth != 'green':
               print("FAIL:", test.testName)
   return False


def precheckHostConnection(vccs, cluster):
   print("Start cluster shutdown power on precheck")
   stats = vccs.GetRuntimeStats(cluster)
   disconnectedHosts = []
   for host in stats:
      if host.stats is None or not host.stats:
         disconnectedHosts.append(host.host)
   if len(disconnectedHosts) > 0:
      print("Disconnected hosts:", disconnectedHosts)
      return False
   return True


def powerOnCluster(si, vccs, vcps, cluster):
   if not precheckHostConnection(vccs, cluster):
      return -1
   powerActionCluster(si, vcps, cluster, "clusterPoweredOn")


def powerOffCluster(si, vchs, vcps, cluster):
   if not precheckHealth(vchs, cluster):
      return -1
   powerActionCluster(si, vcps, cluster, "clusterPoweredOff")


def powerActionCluster(si, vcps, cluster, action):
   cspec = vim.cluster.PerformClusterPowerActionSpec()

   if action == "clusterPoweredOn":
      cspec.targetPowerStatus = "clusterPoweredOn"
   elif action == "clusterPoweredOff":
      cspec.targetPowerStatus = "clusterPoweredOff"
      cspec.powerOffReason = "Scheduled maintenance"

   vsanTask = vcps.PerformClusterPowerAction(cluster, cspec)
   vcTask = vsanapiutils.ConvertVsanTaskToVcTask(vsanTask, si._stub)
   print('Start %s...' % cspec.targetPowerStatus)
   vsanapiutils.WaitForTasks([vcTask], si)
   print('Finish.')


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
   apiVersion = vsanapiutils.GetLatestVmodlVersion(args.host)
   if aboutInfo.apiType == 'VirtualCenter':

      # Get vSAN health system from the vCenter Managed Object references.
      vcMos = vsanapiutils.GetVsanVcMos(
            si._stub, context=context, version=apiVersion)
      vcps = vcMos['vsan-cluster-power-system']
      vchs = vcMos['vsan-cluster-health-system']
      vccs = vcMos['vsan-cluster-config-system']
      cluster = getClusterInstance(args.clusterName, si)

      if cluster is None:
         print("Cluster %s is not found for %s" % (args.clusterName, args.host))
         return -1

      cluster = getClusterInstance(args.clusterName, si)
      powerAction = args.powerAction
      if powerAction == "poweroff":
         powerOffCluster(si, vchs, vcps, cluster)
      elif powerAction == "poweron":
         powerOnCluster(si, vccs, vcps, cluster)
      else:
         print("Invalid power action.")

   else:
      print("Invalid IP address, please provide the vCenter IP")

if __name__ == "__main__":
   main()
