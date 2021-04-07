#!/usr/bin/env python

import ast
import ssl
from pyVmomi import pbm, VmomiSupport
from tools import cli, service_instance

"""
Example of using Storage Policy Based Management (SPBM) API
to update an existing VM Storage Policy.

Required Prviledge: Profile-driven storage update
"""

__author__ = 'William Lam'


# retrieve SPBM API endpoint
def get_pbm_connection(vpxd_stub):
    from http import cookies
    import pyVmomi
    session_cookie = vpxd_stub.cookie.split('"')[1]
    http_context = VmomiSupport.GetHttpContext()
    cookie = cookies.SimpleCookie()
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


# Create required SPBM Capability object from python dict
def _dict_to_capability(d):
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
def update_profile(pm, profile, rules):
    pm.PbmUpdate(
        profileId=profile.profileId,
        updateSpec=pbm.profile.CapabilityBasedProfileUpdateSpec(
            description=None,
            constraints=pbm.profile.SubProfileCapabilityConstraints(
                subProfiles=[
                    pbm.profile.SubProfileCapabilityConstraints.SubProfile(
                        name="vSAN VMC Stretched sub-profile",
                        capability=_dict_to_capability(rules)
                    )
                ]
            )
        )
    )


# Start program
def main():
    parser = cli.Parser()
    parser.add_custom_argument('--policy-name', required=True, action='store',
                               help='VM Storage Policy ID')
    parser.add_custom_argument('--policy-rule', required=True, action='store',
                               help="VM Storage Policy Rule encoded as dictionary"
                               "example:"
                               " \"{\'VSAN.hostFailuresToTolerate\':1,"
                               "    \'VSAN.stripeWidth\':2,"
                               "    \'VSAN.forceProvisioning\':False}\"")
    args = parser.get_args()
    si = service_instance.connect(args)

    # Connect to SPBM Endpoint
    pbm_si, pbm_content = get_pbm_connection(si._stub)

    pm = pbm_content.profileManager
    profile_ids = pm.PbmQueryProfile(
        resourceType=pbm.profile.ResourceType(resourceType="STORAGE"),
        profileCategory="REQUIREMENT"
    )

    profiles = []
    if len(profile_ids) > 0:
        profiles = pm.PbmRetrieveContent(profileIds=profile_ids)

    # Attempt to find profile name given by user
    vm_profile = None
    for profile in profiles:
        if profile.name == args.policy_name:
            vm_profile = profile
            break

    if vm_profile:
        # Convert string to dict
        vm_policy_rules = ast.literal_eval(args.policy_rule)

        print("Updating VM Storage Policy %s with %s ..." % (
            args.policy_name, args.policy_rule))
        update_profile(pm, vm_profile, vm_policy_rules)
    else:
        print("Unable to find VM Storage Policy %s " % args.policy_name)


# Start program
if __name__ == "__main__":
    main()
