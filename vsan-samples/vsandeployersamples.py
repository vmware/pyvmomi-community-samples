#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2022-2024 Broadcom. All Rights Reserved.
The term "Broadcom" refers to Broadcom Inc. and/or its subsidiaries.

This file includes sample codes for vCenter and ESXi sides vSAN API accessing.

To provide an example of ESXi side vSAN API access, it shows how to bootstrap
vSAN ESA from a single ESXi host by invoking the VsanPrepareVsanForVcsa() API
of the VsanVcsaDeployerSystem MO.

To provide an exmaple of VCSA side vSAN API access, it shows how to complete
vSAN ESA bootstrapping on the VCSA by invoking the VsanPostConfigForVcsa() API
of the VsanVcsaDeployerSystem MO.
"""

__author__ = 'Broadcom, Inc'

from pyVim.connect import SmartConnect, Disconnect
import sys
import ssl
import atexit
import argparse
import getpass
import pyVmomi
from pyVmomi import vim
from datetime import datetime
import time
if sys.version[0] < '3':
   input = raw_input

# Import the vSAN API python bindings and utilities.
import vsanmgmtObjects
import vsanapiutils

def GetArgs():
   """
   Supports the command-line arguments listed below.
   """
   parser = argparse.ArgumentParser(description=
'''
General workflow of VC on vSAN bootstrapping:

  1. Use VsanPrepareVsanForVcsa() API to setup vSAN / vSAN ESA datastore on a fresh ESXi host.
     E.g.: ./vsandeployersamples.py -s <host IP> -u <user> -p <pwd>

  2. Use tools like ovftool to deploy VCSA onto the vSAN / vSAN ESA datastore on previous ESXi host

  3. Use VsanPostConfigForVcsa() API to setup the newly installed VCSA, that includes:
     a) creating datacenter & cluster;
     b) add the first host & remaining hosts into the cluster, etc.
     E.g.: ./vsandeployersamples.py -s <VC IP> -u <user> -p <pwd> --datacenter <datacenter to create>
                                    --cluster <cluster to create> --esxIPs <first hostIP> --esxIPs <other host to add>
                                    --esxUserName <esx user name> --esxPassword <esx pwd>

Process args for vSAN SDK sample application:
''', formatter_class=argparse.RawTextHelpFormatter)
   parser.add_argument('-s', '--host', required=True, action='store',
                       help='Remote host to connect to')
   parser.add_argument('-o', '--port', type=int, default=443, action='store',
                       help='Port to connect on')
   parser.add_argument('-u', '--user', required=True, action='store',
                       help='User name to use when connecting to host')
   parser.add_argument('-p', '--password', required=False, action='store',
                       help='Password to use when connecting to host')
   parser.add_argument('--datacenter', required=False, dest='dcName',
                       metavar="DATACENTER", default='DataCenter',
                       help='DataCenter to be created')
   parser.add_argument('--cluster', required=False, dest='clusterName',
                       metavar="CLUSTER", default='vSAN-ESA-Cluster',
                       help='Cluster to be created')
   parser.add_argument('--esxIPs', required=False, dest='esxIPs', nargs='*',
                       metavar="ESXIPS", help='ESX IP to be added into the cluster. Note: The first host must be the one previously bootstrapped vSAN')
   parser.add_argument('--esxUserName', required=False, dest='esxUserName',
                       metavar="ESXUSERNAME", help='username of the ESX to be added into the cluster')
   parser.add_argument('--esxPassword', required=False, dest='esxPassword',
                       metavar="ESXPASSWORD", help='password of the ESX to be added into the cluster')
   args = parser.parse_args()
   return args

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


   if aboutInfo.apiType == 'HostAgent':
      folder = si.content.rootFolder
      dc = folder.childEntity[0]
      hostFolder = dc.hostFolder
      host = hostFolder.childEntity[0].host[0]

      # Make sure vSAN management stack is up on the host
      host.configManager.vsanSystem.QueryDisksForVsan()

      # Get vSAN health system from the ESXi Managed Object references.
      esxMos = vsanapiutils.GetVsanEsxMos(
            si._stub, context=context, version=apiVersion)
      print(esxMos)
      vs = esxMos['vsanSystem']
      disks = vs.QueryDisksForVsan()
      print(disks)
      eligibleDisks = \
      [d.disk for d in disks if d.storagePoolDiskState == 'eligible']

      # Prepare Storage Pool Spec for the creation of vSAN ESA datastore
      spec = vim.vsan.host.AddStoragePoolDiskSpec()
      spec.host = host
      for disk in eligibleDisks:
         storagePoolSpec = vim.vsan.host.StoragePoolDisk()
         storagePoolSpec.diskName = disk.canonicalName
         storagePoolSpec.diskType = vim.vsan.host.StoragePoolDiskType('singleTier')
         spec.disks.append(storagePoolSpec)

      # (Optional) Prepare Native Key Provider Spec to be used for the new vSAN
      # ESA cluster. This can be replaced with other Key Provider/Management Service
      # that's supported by vSAN ESA, or can be skipped if encryption is not
      # intended.
      nativeKeyProviderSpec = vim.vsan.host.CreateNativeKeyProviderSpec(
          provider="NKP_test",
          keyDerivationKey='QPHPZc7MTMEQLB7WkRWkGqxCyTTMHvftlz1zX7uqQQ0=',
          tpmRequired=False,
          keyId = "12345677-abcd-1234-cdef-123456789abc"
      )

      # Send API call to start bootstrapping
      vvds = esxMos['vsan-vcsa-deployer-system']
      vSpec = vim.vsan.VsanPrepareVsanForVcsaSpec(
          vsanAddStoragePoolDiskSpec = spec,
          vsanDataEncryptionConfig = vim.vsan.host.EncryptionInfo(
              enabled=True
          ),
          createNativeKeyProviderSpec = nativeKeyProviderSpec
      )

      # Monitor bootstrapping progress
      taskId = vvds.VsanPrepareVsanForVcsa(spec = vSpec)
      progress = vvds.VsanVcsaGetBootstrapProgress(taskId = [taskId])[0]
      while not progress.success:
         if (progress.error is not None):
            print("Operation Failed: ")
            print(progress.error)
            break
         print("[%s] Current Progress: %s%% - %s" % (datetime.now().strftime('%H:%M:%S'), progress.progressPct, progress.message))
         time.sleep(5)
         progress_t = vvds.VsanVcsaGetBootstrapProgress(taskId = [taskId])
         progress = progress_t[0]

      print('Bootstrapping on ESXi has completed successfully, you can continue to deploy VCSA on the vSAN ESA storage pool of ' \
            'this host, and continue the rest bootstrapping on VCSA')

   if aboutInfo.apiType == 'VirtualCenter':

      vcMos = vsanapiutils.GetVsanVcMos(
            si._stub, context=context, version=apiVersion)
      vvds = vcMos['vsan-vcsa-deployer-system']

      hosts = []
      for host in args.esxIPs:
          hosts.append(vim.HostConnectSpec(
              force = True,
              hostName = host,
              userName = args.esxUserName,
              password = args.esxPassword
          ))

      # NOTE: This MUST be the one used when bootstrapping on the first ESXi
      nativeKeyProviderSpec = vim.vsan.host.CreateNativeKeyProviderSpec(
          provider="NKP_test",
          keyDerivationKey='QPHPZc7MTMEQLB7WkRWkGqxCyTTMHvftlz1zX7uqQQ0=',
          tpmRequired=False,
          keyId = "12345677-abcd-1234-cdef-123456789abc"
      )

      vSpec = vim.VsanVcPostDeployConfigSpec(
          dcName = args.dcName,
          clusterName = args.clusterName,
          firstHost=hosts[0],
          hostsToAdd=hosts[1:],
          vsanDataEncryptionConfig = vim.vsan.host.EncryptionInfo(
              enabled=True,
          ),
          createNativeKeyProviderSpec = nativeKeyProviderSpec
      )

      taskId = vvds.VsanPostConfigForVcsa(spec=vSpec)
      progress = vvds.VsanVcsaGetBootstrapProgress(taskId = [taskId])[0]
      while not progress.success:
         if (progress.error is not None):
            print("Operation Failed: ")
            print(progress.error)
            break
         print("[%s] Current Progress: %s%% - %s" % (datetime.now().strftime('%H:%M:%S'), progress.progressPct, progress.message))
         time.sleep(5)
         progress_t = vvds.VsanVcsaGetBootstrapProgress(taskId = [taskId])
         progress = progress_t[0]

      print('Bootstrapping on VCSA has completed successfully')


if __name__ == "__main__":
   main()
