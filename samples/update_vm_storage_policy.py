#!/usr/bin/env python

from pyVmomi import vim, pbm, VmomiSupport
from tools import cli, service_instance
import ast
import ssl

"""
Example of using Storage Policy Based Management (SPBM) API
to update an existing VM Storage Policy.

Required Prviledge: Profile-driven storage update
"""

__author__ = 'William Lam'


# retrieve SPBM API endpoint
def GetPbmConnection(vpxdStub):
    from http import cookies
    import pyVmomi
    sessionCookie = vpxdStub.cookie.split('"')[1]
    httpContext = VmomiSupport.GetHttpContext()
    cookie = cookies.SimpleCookie()
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
        for k, v in d.items()
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
                        name="vSAN VMC Stretched sub-profile",
                        capability=_dictToCapability(rules)
                    )
                ]
            )
        )
    )


# Start program
def main():
    parser = cli.Parser()
    parser.add_custom_argument('--policy-name', required=True, action='store', help='VM Storage Policy ID')
    parser.add_custom_argument('--policy-rule', required=True, action='store',
                                        help="VM Storage Policy Rule encoded as dictionary"
                                             "example:"
                                             " \"{\'VSAN.hostFailuresToTolerate\':1,"
                                             "    \'VSAN.stripeWidth\':2,"
                                             "    \'VSAN.forceProvisioning\':False}\"")
    args = parser.get_args()
    serviceInstance = service_instance.connect(args)

    # Connect to SPBM Endpoint
    pbmSi, pbmContent = GetPbmConnection(serviceInstance._stub)

    pm = pbmContent.profileManager
    profileIds = pm.PbmQueryProfile(
        resourceType=pbm.profile.ResourceType(resourceType="STORAGE"),
        profileCategory="REQUIREMENT"
    )

    profiles = []
    if len(profileIds) > 0:
        profiles = pm.PbmRetrieveContent(profileIds=profileIds)

    # Attempt to find profile name given by user
    vmProfile = None
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
