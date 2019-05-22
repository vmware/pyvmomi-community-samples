# Written by Chris Arceneaux
# GitHub: https://github.com/carceneaux
# Email: carceneaux@thinksis.com
# Website: http://arsano.ninja
#
# This code has been released under the terms of the Apache-2.0 license
# http://opensource.org/licenses/Apache-2.0

"""
This module implements simple helper functions for working with the
VMware Storage Policy (pbm) API
"""

from pyVmomi import pbm, VmomiSupport


def create_pbm_session(stub):
    """
    Creates a session with the VMware Storage Policy API

    Sample Usage:

    create_pbm_session(service_instance._stub)
    """
    import pyVmomi
    import ssl
    # Make compatible with both Python2/3
    try:
        from http import cookies
    except ImportError:
        import Cookie as cookies

    sessionCookie = stub.cookie.split('"')[1]
    httpContext = VmomiSupport.GetHttpContext()
    cookie = cookies.SimpleCookie()
    cookie["vmware_soap_session"] = sessionCookie
    httpContext["cookies"] = cookie
    VmomiSupport.GetRequestContext()["vcSessionCookie"] = sessionCookie
    hostname = stub.host.split(":")[0]

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

    return pbmSi


def retrieve_storage_policy(pbmContent, policy):
    """
    Retrieves the managed object for the storage policy specified

    Sample Usage:

    pbmContent = pbmSi.RetrieveContent()
    retrieve_storage_policy(pbmContent, "Policy Name")
    """
    # Set PbmQueryProfile
    pm = pbmContent.profileManager

    # Retrieving Storage Policies
    profileIds = pm.PbmQueryProfile(resourceType=pbm.profile.ResourceType(
        resourceType="STORAGE"), profileCategory="REQUIREMENT"
    )
    if len(profileIds) > 0:
        profiles = pm.PbmRetrieveContent(profileIds=profileIds)
    else:
        raise RuntimeError("No Storage Policies found.")

    # Searching for Storage Policy
    profile = None
    for p in profiles:
        if p.name == policy:
            profile = p
            break
    if not profile:
        raise RuntimeError("Storage Policy specified not found.")

    return profile
