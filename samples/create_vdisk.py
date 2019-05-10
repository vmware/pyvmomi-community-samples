#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Written by Chris Arceneaux
# GitHub: https://github.com/carceneaux
# Email: carceneaux@thinksis.com
# Website: http://arsano.ninja
#
# Note: Example code For testing purposes only
#
# This code has been released under the terms of the Apache-2.0 license
# http://opensource.org/licenses/Apache-2.0

"""
Python program for creating a first class disk (fcd)
"""

import atexit

from tools import cli, tasks
from pyVim import connect
from pyVmomi import vmodl, vim, pbm, VmomiSupport


def get_args():
    """
    Adds additional args for creating a fcd

    -d datastore
    -n name
    -c capacityInGB
    -e policy
    -k keepAfterDeleteVm
    """
    parser = cli.build_arg_parser()

    parser.add_argument('-d', '--datastore',
                        required=True,
                        action='store',
                        help='Datastore name where disk is located')

    parser.add_argument('-n', '--name',
                        required=True,
                        action='store',
                        help='First Class Disk name to be created')

    parser.add_argument('-c', '--capacityInGB',
                        required=True,
                        action='store',
                        help='Size in GB of the First Class Disk.',
                        type=int)

    # because -s is reserved for 'service' and -p is reserved for 'password'
    parser.add_argument('-e', '--policy',
                        action='store',
                        help='Storage Policy name. If unset, the default '
                        'policy of the datastore specified will apply.')

    parser.add_argument('-k', '--keepAfterDeleteVm',
                        action='store_true',
                        help='Keep after VM deletion. Choice of the '
                        'deletion behavior of this virtual storage object. '
                        'If not set, the default value is false.')

    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)


def get_obj(content, vimtype, name):
    """
    Retrieves the vmware object for the name and type specified
    """
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def get_pbm_connection(stub):
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
    pbmContent = pbmSi.RetrieveContent()

    return pbmContent


def retrieve_storage_policy(pbmContent, policy):
    """
    Retrieves the vmware object for the storage policy specified
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


def main():
    """
    Simple command-line program for creating a first class disk.
    """

    args = get_args()

    try:
        if args.disable_ssl_verification:
            service_instance = connect.SmartConnectNoSSL(host=args.host,
                                                         user=args.user,
                                                         pwd=args.password,
                                                         port=int(args.port))
        else:
            service_instance = connect.SmartConnect(host=args.host,
                                                    user=args.user,
                                                    pwd=args.password,
                                                    port=int(args.port))

        atexit.register(connect.Disconnect, service_instance)

        content = service_instance.RetrieveContent()

        # Connect to SPBM Endpoint
        pbmContent = get_pbm_connection(service_instance._stub)

        # Retrieving Storage Policy
        if args.policy:
            policy = retrieve_storage_policy(pbmContent, args.policy)
        else:
            policy = None

        # Retrieve Datastore Object
        datastore = get_obj(content, [vim.Datastore], args.datastore)

        # Setting FCD Specifications
        spec = vim.vslm.CreateSpec()
        spec.name = args.name
        spec.capacityInMB = args.capacityInGB * 1024
        if args.keepAfterDeleteVm:
            spec.keepAfterDeleteVm = True
        spec.backingSpec = vim.vslm.CreateSpec.DiskFileBackingSpec()
        spec.backingSpec.provisioningType = "thin"
        spec.backingSpec.datastore = datastore
        if policy:
            spec.profile = [vim.vm.DefinedProfileSpec(
                profileId=policy.profileId.uniqueId)]

        # Create FCD
        storage = content.vStorageObjectManager
        task = storage.CreateDisk_Task(spec)
        tasks.wait_for_tasks(service_instance, [task])

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
