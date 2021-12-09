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

    session_cookie = stub.cookie.split('"')[1]
    http_context = VmomiSupport.GetHttpContext()
    cookie = cookies.SimpleCookie()
    cookie["vmware_soap_session"] = session_cookie
    http_context["cookies"] = cookie
    VmomiSupport.GetRequestContext()["vcSessionCookie"] = session_cookie
    hostname = stub.host.split(":")[0]

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

    return pbm_si


def retrieve_storage_policy(pbm_content, policy):
    """
    Retrieves the managed object for the storage policy specified

    Sample Usage:

    pbm_content = pbm_si.RetrieveContent()
    retrieve_storage_policy(pbm_content, "Policy Name")
    """
    # Set PbmQueryProfile
    profile_manager = pbm_content.profileManager

    # Retrieving Storage Policies
    profile_ids = profile_manager.PbmQueryProfile(resourceType=pbm.profile.ResourceType(
        resourceType="STORAGE"), profileCategory="REQUIREMENT"
    )
    if len(profile_ids) > 0:
        profiles = profile_manager.PbmRetrieveContent(profileIds=profile_ids)
    else:
        raise RuntimeError("No Storage Policies found.")

    # Searching for Storage Policy
    storage_polity_profile = None
    for profile in profiles:
        if profile.name == policy:
            storage_polity_profile = profile
            break
    if not storage_polity_profile:
        raise RuntimeError("Storage Policy specified not found.")

    return storage_polity_profile
