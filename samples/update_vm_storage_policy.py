#!/usr/bin/env python
from pyVmomi import vim, pbm, VmomiSupport
from pyVim.connect import SmartConnect, Disconnect

import atexit
import argparse
import ast
import getpass
import sys
import ssl

"""
Example of using Storage Policy Based Management (SPBM) API
to update an existing VM Storage Policy.

Required Prviledge: Profile-driven storage update
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


# Create required SPBM Capability object from python dict
def _dictToCapability(d):
    return [
        pbm.capability.CapabilityInstance(
            id=pbm.capability.CapabilityMetadata.UniqueId(
                namespace=k.split('.')[0],
                id=k.split('.')[1]
            ),
            constraint=[
                pbm.capability.ConstraintInstance(
                    propertyInstance=[
                        pbm.capability.PropertyInstance(
                            id=k.split('.')[1],
                            value=v
                        )
                    ]
                )
            ]
        )
        for k, v in d.iteritems()
    ]


# Update existing VM Storage Policy
def UpdateProfile(pm, profile, rules):
    pm.PbmUpdate(
        profileId=profile.profileId,
        updateSpec=pbm.profile.CapabilityBasedProfileUpdateSpec(
            description=None,
            constraints=pbm.profile.SubProfileCapabilityConstraints(
                subProfiles=[
                    pbm.profile.SubProfileCapabilityConstraints.SubProfile(
                        name="Object",
                        capability=_dictToCapability(rules)
                    )
                ]
            )
        )
    )


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
    parser.add_argument('-n', '--policy-name', required=True, action='store',
                        help='VM Storage Policy ID')
    parser.add_argument('-r', '--policy-rule', required=True, action='store',
                        help="VM Storage Policy Rule encoded as dictionary"
                        "example:"
                        " \"{\'VSAN.hostFailuresToTolerate\':1,"
                        "    \'VSAN.stripeWidth\':2,"
                        "    \'VSAN.forceProvisioning\':False}\"")
    args = parser.parse_args()
    return args


# Start program
def main():
    args = GetArgs()
    if args.password:
        password = args.password
    else:
        password = getpass.getpass(prompt='Enter password for host %s and '
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
    profileIds = pm.PbmQueryProfile(
        resourceType=pbm.profile.ResourceType(resourceType="STORAGE"),
        profileCategory="REQUIREMENT"
    )

    profiles = []
    if len(profileIds) > 0:
        profiles = pm.PbmRetrieveContent(profileIds=profileIds)

    # Attempt to find profile name given by user
    for profile in profiles:
        if profile.name == args.policy_name:
            vmProfile = profile
            break

    if vmProfile:
        # Convert string to dict
        vmPolicyRules = ast.literal_eval(args.policy_rule)

        print("Updating VM Storage Policy %s with %s ..." % (
            args.policy_name, args.policy_rule))
        UpdateProfile(pm, vmProfile, vmPolicyRules)
    else:
        print("Unable to find VM Storage Policy %s " % args.policy_name)


# Start program
if __name__ == "__main__":
    main()
