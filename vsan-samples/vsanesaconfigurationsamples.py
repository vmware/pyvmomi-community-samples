
"""
Copyright (c) 2022-2024 Broadcom. All Rights Reserved.
The term "Broadcom" refers to Broadcom Inc. and/or its subsidiaries.

This file includes sample code for vCenter to configure vSAN ESA cluster

  - ReconfigureEx

The test setup assumes a vSphere cluster with vCenter version 8.0 and above
"""

__author__ = 'Broadcom, Inc'

import argparse
import sys, platform
import getpass
import ssl
import atexit
import http.cookies
import pyVim
import pyVmomi
from pyVmomi import vim, vmodl, SoapStubAdapter, VmomiSupport, SessionOrientedStub
from pyVim.connect import SmartConnect, Disconnect
import vsanapiutils
import vsanmgmtObjects
from pyVim.task import WaitForTask


def getArgs():
    """
    Supports the command-line arguments listed below.
    """
    parser = argparse.ArgumentParser(description='Process args for vSAN ESA configuration samples')
    parser.add_argument('-s', '--host', required=True, action='store',
                        help='Remote vCenter to connect to')
    parser.add_argument('-o', '--port', type=int, default=443, action='store',
                        help='Port to connect on')
    parser.add_argument('-u', '--user', required=True, action='store',
                        help='User name to use when connecting to vCenter')
    parser.add_argument('-p', '--password', required=False, action='store',
                        help='Password to use when connecting to vCenter')
    parser.add_argument('--cluster', dest='clusterName', metavar="CLUSTER",
                        default='Vsan2Cluster')
    args = parser.parse_args()
    return args


def GetClusterInstance(clusterName, serviceInstance):
    content = serviceInstance.RetrieveContent()
    searchIndex = content.searchIndex
    datacenters = content.rootFolder.childEntity
    for datacenter in datacenters:
        cluster = searchIndex.FindChild(datacenter.hostFolder, clusterName)
        if cluster is not None:
            return cluster
    return None


def VpxdStub2HelathStub(stub):
    version1 = pyVmomi.VmomiSupport.newestVersions.Get("vsan")
    sessionCookie = stub.cookie.split('"')[1]
    httpContext = pyVmomi.VmomiSupport.GetHttpContext()
    cookieObj = http.cookies.SimpleCookie()
    cookieObj["vmware_soap_session"] = sessionCookie
    httpContext["cookies"] = cookieObj
    hostname = stub.host.split(":")[0]
    vhStub = pyVmomi.SoapStubAdapter(host=hostname, version =version1, path = "/vsanHealth", poolSize=0)
    vhStub.cookie = stub.cookie
    return vhStub


def main():
    args = getArgs()
    if args.password:
        password = args.password
    else:
        password = getpass.getpass(prompt='Enter password for vCenter %s and '
                                          'user %s: ' % (args.host, args.user))


    # For python 2.7.9 and later, the default SSL context has more strict
    # connection handshaking rule. We may need turn off the hostname checking
    # and client side cert verification.
    context = None
    if sys.version_info[:3] > (2, 7, 8):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    # Fetch a service instance
    si = SmartConnect(host=args.host,
                      user=args.user,
                      pwd=password,
                      port=int(args.port),
                      sslContext=context)

    atexit.register(Disconnect, si)

    cluster = GetClusterInstance(args.clusterName, si)
    if cluster is None:
        print("Cluster {} is not found for {}".format(args.clusterName, args.host))
        return -1

    # Invoke this API to create HTTP context
    vsanapiutils.GetLatestVmodlVersion(args.host, int(args.port))

    # get vSAN health stub
    vhstub = VpxdStub2HelathStub(si._stub)
    vcs= vim.cluster.VsanVcClusterConfigSystem('vsan-cluster-config-system', vhstub)

    # Step 1) Get the cluster current configuration
    vcs.GetConfigInfoEx(cluster)
    print("Is vSAN ESA enabled:",vcs.GetConfigInfoEx(cluster).vsanEsaEnabled)
    # Step 2) Enable vSAN ESA on the cluster
    rs = vim.vsan.ReconfigSpec(vsanClusterConfig=vim.vsan.cluster.ConfigInfo(enabled=True, vsanEsaEnabled=True))
    tsk = vcs.ReconfigureEx(cluster, rs)
    tsk = vim.Task(tsk._moId, cluster._stub)
    WaitForTask(tsk)
    print(tsk.info)
    # Step 3) Get the updated cluster configuration and notice the vSAN ESA flag enabled.
    vcs.GetConfigInfoEx(cluster)
    print("Is vSAN ESA enabled:",vcs.GetConfigInfoEx(cluster).vsanEsaEnabled)

if __name__ == "__main__":
    main()
