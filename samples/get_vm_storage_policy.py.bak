#!/usr/bin/env python
"""
Written by Vadim Aleksandrov
Github: https://github.com/verdel
Email: valeksandrov@me.com

This code has been released under the terms of the Apache-2.0 license
http://opensource.org/licenses/Apache-2.0

Example of using Storage Policy
Based Management (SPBM) API to get VM Home
and Virtual Disk Storage Policies

Thanks to William Lam (https://github.com/lamw) for ideas from
the script list_vm_storage_policy.py
"""

import atexit
import re
import tools.cli as cli

from pyVmomi import pbm, vim, VmomiSupport, SoapStubAdapter
from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect


def get_args():
    """Supports the command-line arguments listed below.
    """
    parser = cli.build_arg_parser()
    parser.description = 'Show VM Home and Virtual Disk Storage Policies'
    parser.add_argument('-v', '--vm_name',
                        required=True,
                        action='store',
                        metavar='string',
                        help='Get virtual machine by name')
    parser.add_argument('--strict',
                        required=False,
                        action='store_true',
                        help='Search strict virtual machine name matches')
    args = parser.parse_args()
    return cli.prompt_for_password(args)


class bcolors(object):
    """A class used to represent ANSI escape sequences
       for console color output.
    """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def PbmConnect(stubAdapter, disable_ssl_verification=False):
    """Connect to the VMware Storage Policy Server

    :param stubAdapter: The ServiceInstance stub adapter
    :type stubAdapter: SoapStubAdapter
    :param disable_ssl_verification: A flag used to skip ssl certificate
        verification (default is False)
    :type disable_ssl_verification: bool
    :returns: A VMware Storage Policy Service content object
    :rtype: ServiceContent
    """

    if disable_ssl_verification:
        import ssl
        if hasattr(ssl, '_create_unverified_context'):
            sslContext = ssl._create_unverified_context()
        else:
            sslContext = None
    else:
        sslContext = None

    VmomiSupport.GetRequestContext()["vcSessionCookie"] = \
        stubAdapter.cookie.split('"')[1]
    hostname = stubAdapter.host.split(":")[0]
    pbmStub = SoapStubAdapter(
        host=hostname,
        version="pbm.version.version1",
        path="/pbm/sdk",
        poolSize=0,
        sslContext=sslContext)
    pbmSi = pbm.ServiceInstance("ServiceInstance", pbmStub)
    pbmContent = pbmSi.RetrieveContent()
    return pbmContent


def GetStorageProfiles(profileManager, ref):
    """Get vmware storage policy profiles associated with specified entities

    :param profileManager: A VMware Storage Policy Service manager object
    :type profileManager: pbm.profile.ProfileManager
    :param ref: A server reference to a virtual machine, virtual disk,
        or datastore
    :type ref: pbm.ServerObjectRef
    :returns: A list of VMware Storage Policy profiles associated with
        the specified entities
    :rtype: pbm.profile.Profile[]
    """

    profiles = []
    profileIds = profileManager.PbmQueryAssociatedProfile(ref)
    if len(profileIds) > 0:
        profiles = profileManager.PbmRetrieveContent(profileIds=profileIds)
        return profiles
    return profiles


def ShowStorageProfileCapabilities(capabilities):
    """Print vmware storage policy profile capabilities

    :param capabilities: A list of VMware Storage Policy profile
        associated capabilities
    :type capabilities: pbm.capability.AssociatedPolicyCapabilities
    :returns: None
    """

    for capability in capabilities:
        for constraint in capability.constraint:
            if hasattr(constraint, 'propertyInstance'):
                for propertyInstance in constraint.propertyInstance:
                    print("\tKey: {} Value: {}".format(propertyInstance.id,
                                                       propertyInstance.value))


def ShowStorageProfile(profiles):
    """Print vmware storage policy profile

    :param profiles: A list of VMware Storage Policy profiles
    :type profiles: pbm.profile.Profile[]
    :returns: None
    """

    for profile in profiles:
        print("Name: {}{}{} ".format(bcolors.OKGREEN,
                                     profile.name,
                                     bcolors.ENDC))
        print("ID: {} ".format(profile.profileId.uniqueId))
        print("Description: {} ".format(profile.description))
        if hasattr(profile.constraints, 'subProfiles'):
            subprofiles = profile.constraints.subProfiles
            for subprofile in subprofiles:
                print("RuleSetName: {} ".format(subprofile.name))
                capabilities = subprofile.capability
                ShowStorageProfileCapabilities(capabilities)


def SearchVMByName(serviceInstance, name, strict=False):
    """Search virtual machine by name

    :param serviceInstance: A ServiceInstance managed object
    :type name: serviceInstance
    :param name: A virtual machine name
    :type name: str
    :param strict: A flag used to set strict search method
        (default is False)
    :type strict: bool
    :returns: A virtual machine object
    :rtype: VirtualMachine
    """

    content = serviceInstance.content
    root_folder = content.rootFolder
    objView = content.viewManager.CreateContainerView(root_folder,
                                                      [vim.VirtualMachine],
                                                      True)
    vmList = objView.view
    objView.Destroy()
    obj = []
    for vm in vmList:
        if strict:
            if (vm.name == name):
                obj.append(vm)
                return obj
        else:
            if re.match(".*{}.*".format(name), vm.name):
                obj.append(vm)
    return obj


def main():
    """Main program.
    """

    args = get_args()
    serviceInstance = None
    try:
        if args.disable_ssl_verification:
            serviceInstance = SmartConnectNoSSL(host=args.host,
                                                user=args.user,
                                                pwd=args.password,
                                                port=int(args.port))
        else:
            serviceInstance = SmartConnect(host=args.host,
                                           user=args.user,
                                           pwd=args.password,
                                           port=int(args.port))
        atexit.register(Disconnect, serviceInstance)
    except IOError as e:
        print(e)
        pass
    if not serviceInstance:
        raise SystemExit("Unable to connect to host with supplied info.")

    pbm_content = PbmConnect(serviceInstance._stub,
                             args.disable_ssl_verification)
    pm = pbm_content.profileManager

    vm_list = SearchVMByName(serviceInstance, args.vm_name, args.strict)
    for vm in vm_list:
        print("Virtual machine name: {}{}{}".format(bcolors.OKGREEN,
                                                    vm.name,
                                                    bcolors.ENDC))
        pmObjectType = pbm.ServerObjectRef.ObjectType("virtualMachine")
        pmRef = pbm.ServerObjectRef(key=vm._moId,
                                    objectType=pmObjectType)
        profiles = GetStorageProfiles(pm, pmRef)
        if len(profiles) > 0:
            print("Home Storage Profile:")
            ShowStorageProfile(profiles)

        print("\r\nVirtual Disk Storage Profile:")
        for device in vm.config.hardware.device:
            deviceType = type(device).__name__
            if deviceType == "vim.vm.device.VirtualDisk":
                pmObjectType = pbm.ServerObjectRef.ObjectType("virtualDiskId")
                pmRef = pbm.ServerObjectRef(key="{}:{}".format(vm._moId,
                                                               device.key),
                                            objectType=pmObjectType)
                profiles = GetStorageProfiles(pm, pmRef)
                if len(profiles) > 0:
                    print(device.deviceInfo.label)
                    ShowStorageProfile(profiles)
                    print("")
        print("")


if __name__ == "__main__":
    main()
