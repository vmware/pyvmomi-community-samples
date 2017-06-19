#!/usr/bin/env python

import atexit
import argparse
import getpass
import ssl

from pyVmomi import pbm, VmomiSupport
from pyVim.connect import SmartConnect, Disconnect

"""
Example of using Storage Policy Based Management (SPBM) API
to list all VM Storage Policies

Required Prviledge: Profile-driven storage view
"""

__author__ = 'William Lam'


# retrieve SPBM API endpoint
def GetPbmConnection(vpxdStub):
    import Cookie
    import pyVmomi
    sessionCookie = vpxdStub.cookie.split('"')[1]
    httpContext = VmomiSupport.GetHttpContext()
    cookie = Cookie.SimpleCookie()
    cookie["vmware_soap_session"] = sessionCookie
    httpContext["cookies"] = cookie
    VmomiSupport.GetRequestContext()["vcSessionCookie"] = sessionCookie
    hostname = vpxdStub.host.split(":")[0]

    context = None
    if hasattr(ssl, "_create_unverified_context"):
        context = ssl._create_unverified_context()
    pbmStub = pyVmomi.SoapStubAdapter(
        host=hostname,
        version="pbm.version.version1",
        path="/pbm/sdk",
        poolSize=0,
        sslContext=context)
    pbmSi = pbm.ServiceInstance("ServiceInstance", pbmStub)
    pbmContent = pbmSi.RetrieveContent()

    return (pbmSi, pbmContent)


def GetArgs():
    """
    Supports the command-line arguments listed below.
    """
    parser = argparse.ArgumentParser(
        description='Process args for VSAN SDK sample application')
    parser.add_argument('-s', '--host', required=True, action='store',
                        help='Remote host to connect to')
    parser.add_argument('-o', '--port', type=int, default=443, action='store',
                        help='Port to connect on')
    parser.add_argument('-u', '--user', required=True, action='store',
                        help='User name to use when connecting to host')
    parser.add_argument('-p', '--password', required=False, action='store',
                        help='Password to use when connecting to host')
    args = parser.parse_args()
    return args


def showCapabilities(capabilities):
    for capability in capabilities:
        for constraint in capability.constraint:
            if hasattr(constraint, 'propertyInstance'):
                for propertyInstance in constraint.propertyInstance:
                    print("\tKey: %s Value: %s" % (propertyInstance.id,
                                                   propertyInstance.value))


# Start program
def main():
    args = GetArgs()
    if args.password:
        password = args.password
    else:
        password = getpass.getpass(
            prompt='Enter password for host %s and '
                   'user %s: ' % (args.host, args.user))

    context = None
    if hasattr(ssl, "_create_unverified_context"):
        context = ssl._create_unverified_context()
    si = SmartConnect(host=args.host,
                      user=args.user,
                      pwd=password,
                      port=int(args.port),
                      sslContext=context)

    atexit.register(Disconnect, si)

    # Connect to SPBM Endpoint
    pbmSi, pbmContent = GetPbmConnection(si._stub)

    pm = pbmContent.profileManager
    profileIds = pm.PbmQueryProfile(resourceType=pbm.profile.ResourceType(
        resourceType="STORAGE"), profileCategory="REQUIREMENT"
    )

    profiles = []
    if len(profileIds) > 0:
        profiles = pm.PbmRetrieveContent(profileIds=profileIds)

    for profile in profiles:
        print("Name: %s " % profile.name)
        print("ID: %s " % profile.profileId.uniqueId)
        print("Description: %s " % profile.description)
        if hasattr(profile.constraints, 'subProfiles'):
            subprofiles = profile.constraints.subProfiles
            for subprofile in subprofiles:
                print("RuleSetName: %s " % subprofile.name)
                capabilities = subprofile.capability
                showCapabilities(capabilities)
        print("")


# Start program
if __name__ == "__main__":
    main()
