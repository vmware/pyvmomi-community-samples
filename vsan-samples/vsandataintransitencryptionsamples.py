#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2020-2024 Broadcom. All Rights Reserved.
The term "Broadcom" refers to Broadcom Inc. and/or its subsidiaries.

This file includes sample codes for vCenter side vSAN Data-In-Transit
Encryption API accessing.

To provide an example of vCenter side vSAN Data-In-Transit
Encryption API access, it shows how to set data-in-transit encryption setting
on a give cluster by invoking the ReconfigureEx() API of the
VsanVcClusterConfigSystem MO.

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

   if aboutInfo.apiType == 'VirtualCenter':
      majorApiVersion = aboutInfo.apiVersion
      if LooseVersion(majorApiVersion) < LooseVersion('6.7.1'):
         print('The Virtual Center with version %s (lower than 6.7U3) is not '
               'supported.' % aboutInfo.apiVersion)
         return -1

      # Get vSAN health system from the vCenter Managed Object references.
      vcMos = vsanapiutils.GetVsanVcMos(
            si._stub, context=context, version=apiVersion)
      vccs = vcMos['vsan-cluster-config-system']

      cluster = getClusterInstance(args.clusterName, si)

      if cluster is None:
         print('Cluster %s is not found for %s' % (args.clusterName, args.host))
         return -1

      clusterReconfigSpec = vim.vsan.ReconfigSpec()
      clusterReconfigSpec.dataInTransitEncryptionConfig = \
          vim.vsan.DataInTransitEncryptionConfig()

      #Set to True to enable and False to disable data-in-transit encryption.
      #If the value is left unset, it will leave current state unchanged.
      clusterReconfigSpec.dataInTransitEncryptionConfig.enabled = True

      #Periodical rekeying interval in minutes.
      #Default interval is 1440, i.e. 24 hours.
      #For release build, minimal interval is 30 minutes
      #and maximum is 10080, i.e. 7 days.
      clusterReconfigSpec.dataInTransitEncryptionConfig.rekeyInterval = 30

      ditEncryptionConfigTask = vccs.ReconfigureEx(cluster, clusterReconfigSpec)

      ditEncryptionConfigVcTask = vsanapiutils.ConvertVsanTaskToVcTask(
                           ditEncryptionConfigTask, si._stub)
      vsanapiutils.WaitForTasks([ditEncryptionConfigVcTask], si)

      print('Set vSAN data-in-transit encryption finished with '
            'status: %s' % ditEncryptionConfigVcTask.info.state)
   else:
      print('Remove host should be a Virtual Center ')
      return -1

if __name__ == "__main__":
   main()
