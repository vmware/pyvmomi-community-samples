#!/usr/bin/env python

import ssl
from pyVmomi import pbm, VmomiSupport
from tools import cli, service_instance

"""
Example of using Storage Policy Based Management (SPBM) API
to list all VM Storage Policies

Required Prviledge: Profile-driven storage view
"""

__author__ = 'William Lam'

# retrieve SPBM API endpoint
def GetPbmConnection(vpxdStub):
    import http.cookies as Cookie
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


def showCapabilities(capabilities):
    for capability in capabilities:
        for constraint in capability.constraint:
            if hasattr(constraint, 'propertyInstance'):
                for propertyInstance in constraint.propertyInstance:
                    print("\tKey: %s Value: %s" % (propertyInstance.id,
                                                   propertyInstance.value))


# Start program
def main():
    parser = cli.Parser()
    args = parser.get_args()
    serviceInstance = service_instance.connect(args)

    # Connect to SPBM Endpoint
    pbmSi, pbmContent = GetPbmConnection(serviceInstance._stub)

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
