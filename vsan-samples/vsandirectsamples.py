#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2020-2024 Broadcom. All Rights Reserved.
The term "Broadcom" refers to Broadcom Inc. and/or its subsidiaries.

This file includes sample code for the vSAN Direct API.

To provide an example of vSAN direct API access, it shows how to query eligible
disks, claim vSAN direct storages and query vsan direct storages.

NOTE: this sample can only be run against vc whose version is equal
to or higher than 7.0 u1.

usage: vsandirectsamples.py [-h] -s HOST [-o PORT] -u USER [-p PASSWORD] [--cluster CLUSTER]
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
from pyVim import task

import pyVmomi
import vsanmgmtObjects

if sys.version[0] < '3':
   input = raw_input

def main():
   args = GetArgs()
   (si, cluster, vdms) = connectToServers(args)

   if cluster is None:
      print("Cluster %s is not found for %s" % (args.clusterName, args.host))
      return -1

   # Query available disks
   hostDisks = {}
   hosts = cluster.host
   for host in hosts:
      disks = host.configManager.vsanSystem.QueryDisksForVsan()
      eligibleDisks = [d.disk for d in disks if d.state == 'eligible']
      hostDisks[host.name] = eligibleDisks
   outPutEligibleDisks = dict(
      [(h, [d.canonicalName for d in hostDisks[h]]) for h in hostDisks])
   print("Eligible disks: %s" % outPutEligibleDisks)

   # Claim vSAN direct storages
   for host in hosts:
      eligibleDisks = hostDisks.get(host.name)
      if eligibleDisks:
         spec = vim.vsan.host.DiskMappingCreationSpec()
         spec.host = host
         spec.capacityDisks = [eligibleDisks[0]]
         spec.creationType = "vsandirect"
         print("Claiming disks %s for host %s" % \
           (eligibleDisks[0].canonicalName, host.name))
         tsk = vdms.InitializeDiskMappings(spec)
         tsk = vim.Task(tsk._moId, si._stub)
         if (task.WaitForTask(tsk) != vim.TaskInfo.State.success):
            raise Exception("%s diskmapping creation task failed %s" % \
               (spec.creationType, tsk.info))
         print("Succeed in claiming disk for host %s" % host.name)

   # Query vSAN direct storages
   result = {}
   for host in cluster.host:
      ret = vdms.QueryVsanManagedDisks(host)
      retDisks = set()
      result[host.name] = retDisks
      for vsanDirectStorage in ret.vSANDirectDisks:
         retDisks.update(
            [disk.canonicalName for disk in vsanDirectStorage.scsiDisks])
   print("vSAN direct storages: %s" % result)

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
   Creates connections to the vCenter, vSAN and vSAN disk mangement system
   @param args
   @return vc service instance, cluster, vSAN disk management system
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
   si = SmartConnect(host=args.host,
                     user=args.user,
                     pwd=password,
                     port=int(args.port),
                     sslContext=sslContext)
   atexit.register(Disconnect, si)

   # Get vSAN service instance stub
   apiVersion = vsanapiutils.GetLatestVmodlVersion(args.host, int(args.port))
   aboutInfo = si.content.about
   if aboutInfo.apiType != 'VirtualCenter':
      raise Exception("The sample script should be run against vc.")

   vsanStub = vsanapiutils.GetVsanVcMos(si._stub,
                                     context = sslContext,
                                     version = apiVersion)

   # Get vSAN disk management system
   vdms = vsanStub['vsan-disk-management-system']

   # Get cluster
   cluster = getClusterInstance(args.clusterName, si)

   return (si, cluster, vdms)

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
