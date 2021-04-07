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
def get_pbm_connection(vpxd_stub):
    import http.cookies as http_cookies
    import pyVmomi
    session_cookie = vpxd_stub.cookie.split('"')[1]
    http_context = VmomiSupport.GetHttpContext()
    cookie = http_cookies.SimpleCookie()
    cookie["vmware_soap_session"] = session_cookie
    http_context["cookies"] = cookie
    VmomiSupport.GetRequestContext()["vcSessionCookie"] = session_cookie
    hostname = vpxd_stub.host.split(":")[0]

    context = None
    if hasattr(ssl, "_create_unverified_context"):
        context = ssl._create_unverified_context()
    pbm_stub = pyVmomi.SoapStubAdapter(
        host=hostname,
        version="pbm.version.version1",
        path="/pbm/sdk",
        poolSize=0,
        sslContext=context)
    pbm_si = pbm.ServiceInstance("ServiceInstance", pbm_stub)
    pbm_content = pbm_si.RetrieveContent()

    return pbm_si, pbm_content


def show_capabilities(capabilities):
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
    si = service_instance.connect(args)

    # Connect to SPBM Endpoint
    pbm_si, pbm_content = get_pbm_connection(si._stub)

    pm = pbm_content.profileManager
    profile_ids = pm.PbmQueryProfile(resourceType=pbm.profile.ResourceType(
        resourceType="STORAGE"), profileCategory="REQUIREMENT"
    )

    profiles = []
    if len(profile_ids) > 0:
        profiles = pm.PbmRetrieveContent(profileIds=profile_ids)

    for profile in profiles:
        print("Name: %s " % profile.name)
        print("ID: %s " % profile.profileId.uniqueId)
        print("Description: %s " % profile.description)
        if hasattr(profile.constraints, 'subProfiles'):
            subprofiles = profile.constraints.subProfiles
            for subprofile in subprofiles:
                print("RuleSetName: %s " % subprofile.name)
                capabilities = subprofile.capability
                show_capabilities(capabilities)
        print("")


# Start program
if __name__ == "__main__":
    main()
