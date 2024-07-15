#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2020-2024 Broadcom. All Rights Reserved.
The term "Broadcom" refers to Broadcom Inc. and/or its subsidiaries.

This file includes sample code for customize the thresholds for vSAN health
checks.

NOTE: this sample can only work on VC with version >= 7.0 U2.

usage: vsandirectsamples.py [-h] -s VC [-o PORT] -u USER [-p PASSWORD]
 [--cluster CLUSTER]
  -h, --help            show this help message and exit
  -s VC, --vc VC  Remote vCenter server to connect to
  -o PORT, --port PORT  Port to connect on
  -u USER, --user USER  User name to use when connecting to VC
  -p PASSWORD, --password PASSWORD
                        Password to use when connecting to VC
  --cluster CLUSTER

"""

__author__ = 'Broadcom, Inc'

import sys
import ssl
import atexit
import argparse
import getpass
import vsanapiutils
import time
from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
from pyVim import task


def main():
   args = GetArgs()
   (si, cluster, ccs, chs) = connectToServers(args)

   if cluster is None:
      print("Cluster %s is not found for %s" % (args.clusterName, args.vc))
      return -1

   # print the current customized threshold
   cluster_config = ccs.GetConfigInfoEx(cluster)
   print("Current customized thresholds value is:")
   print(cluster_config.vsanHealthConfig.healthCheckThresholdSpec)

   # Set customized thresholds for vSAN datastore, vSAN Direct datastore and
   # vSAN managed PMem datastore
   vsanReconfigSpec = vim.vsan.ReconfigSpec(
      vsanHealthConfig = vim.vsan.VsanHealthConfigSpec(
         healthCheckThresholdSpec = [
            vim.vsan.VsanHealthThreshold(
               yellowValue=44,
               redValue=55,
               enabled=True,
               target=
               vim.vsan.VsanHealthThresholdTarget.diskspace_vsan_datastore
            ),
            vim.vsan.VsanHealthThreshold(
               yellowValue=66,
               redValue=77,
               enabled=True,
               target=vim.vsan.VsanHealthThresholdTarget.diskspace_vsan_direct
            ),
            vim.vsan.VsanHealthThreshold(
               yellowValue=88,
               redValue=99,
               enabled=True,
               target=vim.vsan.VsanHealthThresholdTarget.diskspace_vsan_pmem
            ),
         ]
      )
   )
   ccs.ReconfigureEx(cluster, vsanReconfigSpec)
   # Print the customized thresholds by vsan vc config system
   print("Sleep for 10 seconds to wait the customized thresholds take effect")
   time.sleep(10)
   cluster_config = ccs.GetConfigInfoEx(cluster)
   print("Now the customized thresholds have been changed to:")
   print(cluster_config.vsanHealthConfig.healthCheckThresholdSpec)

def GetArgs():
   """
   Supports the command-line arguments listed below.
   """
   parser = argparse.ArgumentParser(
       description='Process args for vSAN SDK sample application')
   parser.add_argument('-s', '--vc', required=True, action='store',
                       help='Remote vCenter Server to connect to')
   parser.add_argument('-o', '--port', type=int, default=443, action='store',
                       help='Port to connect on')
   parser.add_argument('-u', '--user', required=True, action='store',
                       help='User name to use when connecting to Server')
   parser.add_argument('-p', '--password', required=False, action='store',
                       help='Password to use when connecting to Server')
   parser.add_argument('--cluster', dest='clusterName', metavar="CLUSTER",
                       default='VSAN-Cluster')
   args = parser.parse_args()
   return args

def connectToServers(args):
   """
   Creates connections to the vCenter, vSAN and vSAN disk mangement system
   @param args
   @return vc service instance, cluster, vSAN disk management system
   """
   if args.password:
      password = args.password
   else:
      password = getpass.getpass(prompt='Enter password for vc %s and '
                                        'user %s: ' % (args.vc, args.user))

   # For python 2.7.9 and later, the default SSL context has stricter
   # connection handshaking rule, hence we are turning off the hostname checking
   # and client side cert verification.
   sslContext = None
   if sys.version_info[:3] > (2,7,8):
      sslContext = ssl.create_default_context()
      sslContext.check_hostname = False
      sslContext.verify_mode = ssl.CERT_NONE

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
   ccs = vsanStub['vsan-cluster-config-system']
   chs = vsanStub['vsan-cluster-health-system']

   # Get cluster
   cluster = getClusterInstance(args.clusterName, si)

   return (si, cluster, ccs, chs)

def getClusterInstance(clusterName, serviceInstance):
   content = serviceInstance.RetrieveContent()
   searchIndex = content.searchIndex
   datacenters = content.rootFolder.childEntity
   for datacenter in datacenters:
      cluster = searchIndex.FindChild(datacenter.hostFolder, clusterName)
      if cluster is not None:
         return cluster
   return None

if __name__ == "__main__":
   main()
