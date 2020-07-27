#!/usr/bin/env python
"""
Sync's target replication data with source replication data.
Called at the target server. Provide the target replication
group and the name of the point in time replica object to be
created. The created SyncReplicationGroup_Task object is used
to sync the target with source replication group.
smsTaskInfo object is returned that provides information about
the task.
Required Prviledge: StorageViews.ConfigureService
                    to use all Storage Monitoring Service APIs
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
    parser.add_argument('-n',
                        '--pit_name',
                        required=False,
                        action='store',
                        help='pit name to be used')

    args = parser.parse_args()

    cli.prompt_for_password(args)
    return args


def get_id_from_names(vasa_provider, rg_names):
    """
    Get id of replication groups given name
    """
    rg_ids = []
    r_groups = vasa_provider.QueryReplicationGroup()
    for r_group in r_groups:
        for rg_name in rg_names:
            if rg_name == r_group.groupId.deviceGroupId.id:
                rg_ids.append(r_group.groupId)
    return rg_ids


def sync_replication_group(vasa_provider, pit_name, rg_ids):
    """
    sync target replication group data with source replication group data
    creates a point in time replication object which
    wil be used during failover.
    """
    syncGroup = vasa_provider.SyncReplicationGroup_Task(rg_ids, pit_name)
    print('\n')
    print(syncGroup.QuerySmsTaskInfo())


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

    # provide pit_name as parameter.
    if args.pit_name:
        pit_name = args.pit_name
    else:
        pit_name = input('Enter pit name.. ')

    rg_names = []
    if args.rg_names:
        rg_names = args.rg_names

    rg_ids = []
    for vasa_provider in sms_provider:
        try:
            if rg_names:
                rg_ids = get_id_from_names(vasa_provider, rg_names)
            else:
                rgs = vasa_provider.QueryReplicationGroup()
                for rg in rgs:
                    rg_ids.append(rg.groupId)
            sync_replication_group(vasa_provider, pit_name, rg_ids)
        except sms.fault.QueryExecutionFault:
            pass
        except sms.fault.InactiveProvider:
            pass


# Start program
if __name__ == "__main__":
    main()
