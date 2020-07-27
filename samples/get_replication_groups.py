#!/usr/bin/env python
"""
Retrives replication groups at server. Can filter
based on replication group names provided.
Displays the replication groups in the
VASA provider on the server.
Required Prviledge: StorageViews.View
                    to use read-only Storage Monitoring Service APIs.
"""

import atexit
import ssl

from http import cookies
from pyVim.connect import Disconnect, SmartConnectNoSSL
from pyVmomi import SoapStubAdapter, VmomiSupport, sms
from tools import cli

__author__ = 'Miriam John K'


def get_sms_connection(vpxd_stub):
    """
    Retrieve SMS API endpoint
    """
    session_cookie = vpxd_stub.cookie.split('"')[1]
    http_context = VmomiSupport.GetHttpContext()
    cookie = cookies.SimpleCookie()
    cookie["vmware_soap_session"] = session_cookie
    http_context["cookies"] = cookie
    VmomiSupport.GetRequestContext()["vcSessionCookie"] = session_cookie
    hostname = vpxd_stub.host.split(":")[0]
    context = ssl._create_unverified_context()
    sms_stub = SoapStubAdapter(host=hostname,
                               version="sms.version.version14",
                               path="/sms/sdk",
                               poolSize=0,
                               sslContext=context)
    sms_si = sms.ServiceInstance("ServiceInstance", sms_stub)
    return sms_si


def get_args():
    """
    Supports the command-line arguments listed below.
    """
    parser = cli.build_arg_parser()

    parser.add_argument("-r",
                        "--rg_names",
                        required=False,
                        action="store",
                        nargs="*",
                        default=[],
                        help="Name of replication groups.Provide replication"
                        "names as space separated strings.In case of"
                        "target replication groups the name will be"
                        "the device GroupId.")

    args = parser.parse_args()

    cli.prompt_for_password(args)
    return args


def get_replication_groups(vasa_provider, rg_ids=[], rg_names=[]):
    """
    Displays Replication group id, state and name
    """
    r_groups = vasa_provider.QueryReplicationGroup(rg_ids)
    if not rg_names:
        for r_group in r_groups:
            print("\n")
            print("Replication group Id: \n\tdevice Id: {}"
                  "\n\tfault domain Id: {}".format(
                      r_group.groupId.deviceGroupId.id,
                      r_group.groupId.faultDomainId.id))
            if hasattr(r_group, "rgInfo"):
                if hasattr(r_group.rgInfo, "name"):
                    print("Source Replication Group Name: ",
                          r_group.rgInfo.name)
                print("State: ", r_group.rgInfo.state)
        print("\n")
    else:
        for r_group in r_groups:
            if hasattr(r_group, "rgInfo"):
                for rg_name in rg_names:
                    if hasattr(r_group.rgInfo, "name"):
                        if ((r_group.rgInfo.name == rg_name) or
                            (rg_name == r_group.groupId.deviceGroupId.id)):
                            print("\n")
                            print("Source Replication Group Name: ",
                                  r_group.rgInfo.name)
                            print("State: ", r_group.rgInfo.state)
                            print("Replication group Id: \n\tdevice Id: {}"
                                  "\n\tfault domain Id: {}".format(
                                      r_group.groupId.deviceGroupId.id,
                                      r_group.groupId.faultDomainId.id))
                    else:
                        if (rg_name == r_group.groupId.deviceGroupId.id):
                            print("\n")
                            print("Replication group Id: \n\tdevice Id: {}"
                                  "\n\tfault domain Id: {}".format(
                                      r_group.groupId.deviceGroupId.id,
                                      r_group.groupId.faultDomainId.id))
                            print("State: ", r_group.rgInfo.state)
        print("\n")


# Start program
def main():
    args = get_args()

    si = SmartConnectNoSSL(host=args.host,
                           user=args.user,
                           pwd=args.password,
                           port=int(args.port))
    atexit.register(Disconnect, si)

    # Connect to SMS Endpoint
    sms_si = get_sms_connection(si._stub)
    sms_provider = sms_si.QueryStorageManager().QueryProvider()

    # query and display replication groups
    rg_ids = []
    for vasa_provider in sms_provider:
        try:
            rgs = vasa_provider.QueryReplicationGroup()
            for rg in rgs:
                rg_ids.append(rg.groupId)
        except sms.fault.QueryExecutionFault:
            pass

    rg_names = []
    if args.rg_names:
        rg_names = args.rg_names
    for vasa_provider in sms_provider:
        try:
            get_replication_groups(vasa_provider, rg_ids, rg_names)
        except sms.fault.QueryExecutionFault:
            pass
        except sms.fault.InactiveProvider:
            pass


# Start program
if __name__ == "__main__":
    main()
