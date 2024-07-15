#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2021-2024 Broadcom. All Rights Reserved.
The term "Broadcom" refers to Broadcom Inc. and/or its subsidiaries.

This file includes sample codes for the vSphere HCI API to
set up an entire cluster, including DRS, vSAN, HA, vDS, ESX networking
and core ESX services..

It takes four steps ro build a HCI Cluster:
1.create datacenter by calling API CreateDatacenter().
2.create cluster in datacenter by calling API CreateClusterEx().
3.add host to cluster by calling API AddHost_Task().
4.configure HCI by enabling vSAN using API ConfigureHCI_Task().

The API ConfigureHCI_Task() is available since vSphere 6.7 Update 1 release.

"""

__author__ = 'Broadcom, Inc'
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
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
from subprocess import Popen, PIPE

datacenterName = "HCI-Datacenter"
clusterName = "VSAN-Cluster"


class DrsInfo:
   def __init__(self,
                enabled=True,
                vmotionRate=5,
                behavior=vim.cluster.DrsConfigInfo.DrsBehavior.fullyAutomated):
      self.enabled = enabled
      self.vmotionRate = vmotionRate
      self.behavior = behavior

   def ToDrsConfig(self):
      drsConfig =vim.cluster.DrsConfigInfo()
      drsConfig.enabled = self.enabled
      drsConfig.defaultVmBehavior = self.behavior
      drsConfig.vmotionRate = self.vmotionRate
      return drsConfig

def GetArgs():
   """
   Supports the command-line arguments listed below.
   """
   parser = argparse.ArgumentParser(
       description='Process args for vSAN SDK sample application')
   parser.add_argument('-i', '--vc', required=True, action='store',
                       help='IP of vCenter')
   parser.add_argument('-u', '--user', required=True, action='store',
                       help='User name to use when connecting to host')
   parser.add_argument('-p', '--password', required=False, action='store',
                       help='Password to use when connecting to host')
   parser.add_argument('-ips', '--hostIps', required=True, action='store',
                       help='IPs of the hosts to be added to the cluster,\
                             The IPs of the hosts, splitted by commar')
   parser.add_argument('-hu', '--hostUsername', required=True, action='store',
                       help='Username of the hosts')
   parser.add_argument('-hp', '--hostPassword', required=True, action='store',
                       help='Password of the hosts')
   args = parser.parse_args()
   return args

def getSslThumbprint(addr):
   import ssl
   import socket
   import hashlib

   sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   sock.settimeout(1)
   wrappedSocket = ssl.wrap_socket(sock)
   thumbPrint = None
   try:
      wrappedSocket.connect((addr, 443))
   except:
      response = False
   else:
      der_cert_bin = wrappedSocket.getpeercert(True)
      pem_cert = ssl.DER_cert_to_PEM_cert(wrappedSocket.getpeercert(True))
      thumb_sha1 = hashlib.sha1(der_cert_bin)
      thumb_sha1 = str(hashlib.sha1(der_cert_bin).hexdigest()).upper()
      thumbPrint = ":".join(a+b for a,b in\
            zip(thumb_sha1[::2], thumb_sha1[1::2]))
   wrappedSocket.close()
   return thumbPrint

def CreateHostConfigProfile(ntpServer, lockdownMode):
   ntpServers = [ntpServer]
   ntpConfig = vim.HostNtpConfig(server=ntpServers)
   dateTimeConfig = vim.HostDateTimeConfig(ntpConfig=ntpConfig)
   hostConfigProfile = \
       vim.ClusterComputeResource.\
       HostConfigurationProfile(dateTimeConfig=dateTimeConfig,
                                lockdownMode=lockdownMode)
   return hostConfigProfile

def GetVcProf():
   drsInfo = \
       DrsInfo(vmotionRate=2,
               behavior=vim.cluster.DrsConfigInfo.DrsBehavior.fullyAutomated)

   vcProf = vim.ClusterComputeResource.VCProfile()
   configSpec = vim.cluster.ConfigSpecEx()
   configSpec.drsConfig = drsInfo.ToDrsConfig()
   vcProf.clusterSpec = configSpec
   vcProf.evcModeKey = "intel-merom"

   return vcProf

def GetFreePnicList(host):
   networkSystem = host.configManager.networkSystem
   # pnic spec will have a non-NULL entry for linkSpeed if the pnic
   # link-state is UP.
   allUpPnics = list(map(lambda z: z.device,
      filter(lambda x: x.linkSpeed is not None, networkSystem.networkInfo.pnic)))
   # Iterate through all vswitches and read the uplink devices
   # connected to each.
   usedNicsOnVss = list(map(lambda z: z.spec.bridge.nicDevice,
      filter(lambda x: x.spec.bridge is not None and
         len(x.spec.bridge.nicDevice) != 0, networkSystem.networkInfo.vswitch)))
   # Iterate through all vds'es and read the uplink devices connected to each.
   # Firstly, obtain the list of all proxySwitches
   # that have a non-empty list of uplinks.
   # From this list, create a list of pnic objects. The pnic object is of type
   # pyVmomi.VmomiSupport.Link[], and the first element within that list has the
   # pnic name.
   usedNicsOnProxy = list(map(lambda y: y[0],
      map(lambda z: z.pnic,
      filter(lambda x: x.pnic is not None and len(x.pnic) > 0,
      host.config.network.proxySwitch))))

   usedVssPnics = []
   if len(usedNicsOnVss) > 1:
      """
      In this case, usedVnicsOnVss returns an array of type:
      [(str) [ 'vmnic0' ], (str) [ 'vmnic5' ]]
      To obtain the entire list of vmnics, we need to read the first
      element saved in pyVmomi.VmomiSupport.str[].
      """
      usedVssPnics = list(map(lambda x: x[0], usedNicsOnVss))
   elif len(usedNicsOnVss) == 1:
      """
      There's only one used vnic, e.g:
      (str) [ 'vmnic0' ]
      """
      usedVssPnics = list(filter(lambda x: x, usedNicsOnVss[0]))

   if usedNicsOnProxy:
      # usedNicsOnProxy[0] is a Link[], each element of which looks like
      # 'key-vim.host.PhysicalNic-vmnic1'
      pnicsOnProxy = list(map(lambda x: str(x.split('-')[-1]), usedNicsOnProxy))
      usedVssPnics += pnicsOnProxy

   freePnics = set(allUpPnics) - set(usedVssPnics)

   if len(freePnics) >= 1:
      return freePnics
   return []

def CreateDvpgSpec(dvpgName):
    dvpgSpec = vim.dvs.DistributedVirtualPortgroup.ConfigSpec()
    dvpgSpec.numPorts = 128
    dvpgSpec.name = dvpgName
    dvpgSpec.type = "earlyBinding"
    return dvpgSpec

def CreateDvsProfile(dvsName, pnicDevices, dvpgNameAndService,
                     dvsMoRef=None, dvpgMoRefAndService=None):
    dvsProf = vim.ClusterComputeResource.DvsProfile()
    dvsProf.pnicDevices = pnicDevices
    dvsProf.dvsName = dvsName
    dvsProf.dvSwitch = dvsMoRef
    dvpgToServiceMappings = []

    if dvpgNameAndService is not None:
        # Populate the dvportgroup mappings with dvportgroup specs.
        for dvpgName, service in dvpgNameAndService:
            dvpgToServiceMapping =\
                vim.ClusterComputeResource.\
                DvsProfile.DVPortgroupSpecToServiceMapping(
                    dvPortgroupSpec=CreateDvpgSpec(dvpgName),
                    service=service)
            dvpgToServiceMappings.append(dvpgToServiceMapping)
    if dvpgMoRefAndService is not None:
        # Populate the dvportgroup mappings with dvportgroup MoRefs.
        for dvpgMoRef, service in dvpgMoRefAndService:
            dvpgToServiceMapping =\
                vim.ClusterComputeResource.\
                DvsProfile.DVPortgroupSpecToServiceMapping(
                    dvPortgroup=dvpgMoRef, service=service)
            dvpgToServiceMappings.append(dvpgToServiceMapping)
    dvsProf.dvPortgroupMapping = dvpgToServiceMappings
    return dvsProf

def GetDvsProfiles(hosts):
   dvpgNameAndService = [
       ("vmotion-dvpg", "vmotion"),
       ("vsan-dvpg", "vsan")]

   dvsName = "hci-dvs-new"
   freePnic = list(GetFreePnicList(hosts[0]))[0]

   # setup DVS profile
   dvsProf = CreateDvsProfile(dvsName, freePnic, dvpgNameAndService)

   return [dvsProf]

def CreateDefaultVSanSpec(vSanCfgInfo):
    dedupConfig = vim.vsan.DataEfficiencyConfig(dedupEnabled=False)
    encryptionConfig = \
        vim.vsan.DataEncryptionConfig(encryptionEnabled=False)

    vSanSpec = vim.vsan.ReconfigSpec(
        vsanClusterConfig=vSanCfgInfo,
        dataEfficiencyConfig=dedupConfig,
        dataEncryptionConfig=encryptionConfig,
        modify=True,
        allowReducedRedundancy=False
    )
    return vSanSpec

def main():
   args = GetArgs()
   if args.password:
      password = args.password
   else:
      password = getpass.getpass(prompt='Enter password for VC %s and '
                                 'user %s: ' % (args.vc,args.user))
   if args.hostPassword:
      hostPassword = args.hostPassword
   else:
      hostPassword = getpass.getpass(prompt='Enter password for Esxi %s and '
                              'user %s: ' % (args.vcIps,args.hostUsername))

   # For python 2.7.9 and later, the default SSL context has more strict
   # connection handshaking rule. We may need turn off the hostname checking
   # and client side cert verification.
   context = None
   if sys.version_info[:3] > (2,7,8):
      context = ssl.create_default_context()
      context.check_hostname = False
      context.verify_mode = ssl.CERT_NONE

   si = SmartConnect(host=args.vc,
                     user=args.user,
                     pwd=password,
                     port=443,
                     sslContext=context)

   atexit.register(Disconnect, si)

   # Detecting whether the vcis vCenter or ESXi.
   aboutInfo = si.content.about

   if aboutInfo.apiType != 'VirtualCenter':
      print("The HCI APIs are only available on vCenter")
      exit(1)

   folder = si.content.rootFolder
   dc = folder.CreateDatacenter(datacenterName)
   print("Create datacenter %s succeeded" % datacenterName)
   hostFolder = dc.hostFolder
   clusterSpec = vim.ClusterConfigSpecEx(
                  inHciWorkflow = True)
   vsanConfig = vim.vsan.cluster.ConfigInfo()
   vsanConfig.enabled = True
   clusterSpec.vsanConfig = vsanConfig
   cluster = hostFolder.CreateClusterEx(name = clusterName, spec = clusterSpec)
   print("Create cluster %s succeeded" % clusterName)

   hostIps = args.hostIps.split(',')
   tasks = []
   hostSpecs = []
   hostFolder = dc.hostFolder
   for hostIp in hostIps:
      hostSpec = vim.Folder.NewHostSpec()
      sslThumbprint = getSslThumbprint(hostIp)
      hostConnSpec = vim.HostConnectSpec(hostName=hostIp,
                                    userName=args.hostUsername,
                                    force=True,
                                    port=443,
                                    password=hostPassword,
                                    sslThumbprint=sslThumbprint,
                                    )
      hostSpec.hostCnxSpec = hostConnSpec
      hostSpecs.append(hostSpec)
   task = hostFolder.BatchAddHostsToCluster_Task(cluster,
                                            hostSpecs,
                                            None,
                                            None,
                                            'maintenance')
   print("Adding host ...")
   tasks.append(task)
   vsanapiutils.WaitForTasks(tasks, si)
   print("Configuring HCI for cluster %s ..." % clusterName)
   hciCfgs =[]
   for mo in cluster.host:
      hciCfg = vim.ClusterComputeResource.HostConfigurationInput()
      hciCfg.host = mo
      hciCfgs.append(hciCfg)
   lockdownMode = \
         vim.host.HostAccessManager.LockdownMode.lockdownDisabled
   NTP_SERVER = "time-c-b.nist.gov"
   hostConfigProfile = CreateHostConfigProfile(NTP_SERVER, lockdownMode)
   vSanCfgInfo = vim.vsan.cluster.ConfigInfo(
           enabled=True,
           defaultConfig=vim.vsan.cluster.ConfigInfo.HostDefaultInfo(
           autoClaimStorage=False))
   vSanSpec = CreateDefaultVSanSpec(vSanCfgInfo)
   vcProf = GetVcProf()
   dvsProfiles = GetDvsProfiles(cluster.host)
   clusterHciSpec = vim.ClusterComputeResource.HCIConfigSpec(
                       hostConfigProfile=hostConfigProfile,
                       vSanConfigSpec=vSanSpec,
                       vcProf=vcProf,
                       dvsProf=dvsProfiles)

   task=cluster.ConfigureHCI_Task(clusterSpec = clusterHciSpec,\
                                  hostInputs = hciCfgs)
   vsanapiutils.WaitForTasks([task], si)
   print("Successfully configured HCI cluster %s" % clusterName)

   # vSAN cluster health summary can be cached at vCenter.
   apiVersion = vsanapiutils.GetLatestVmodlVersion(args.vc, port=443)
   vcMos = vsanapiutils.GetVsanVcMos(
         si._stub, context=context, version=apiVersion)
   vhs = vcMos['vsan-cluster-health-system']
   fetchFromCache = True
   fetchFromCacheAnswer = input(
      'Do you want to fetch the cluster health from cache if exists?(y/n):')
   if fetchFromCacheAnswer.lower() == 'n':
      fetchFromCache = False
   print('Fetching cluster health from cached state: %s' %
          ('Yes' if fetchFromCache else 'No'))
   healthSummary = vhs.QueryClusterHealthSummary(
      cluster=cluster, includeObjUuids=True, fetchFromCache=fetchFromCache)
   clusterStatus = healthSummary.clusterStatus

   print("Cluster %s Status: %s" % (clusterName, clusterStatus.status))
   for hostStatus in clusterStatus.trackedHostsStatus:
      print("Host %s Status: %s" % (hostStatus.hostname, hostStatus.status))

if __name__ == "__main__":
   main()
