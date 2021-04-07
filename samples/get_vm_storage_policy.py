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

import re
import tools.cli as cli
from pyVmomi import pbm, vim, VmomiSupport, SoapStubAdapter
from tools import service_instance


class BColors(object):
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


def pbm_connect(stub_adapter, disable_ssl_verification=False):
    """Connect to the VMware Storage Policy Server

    :param stub_adapter: The ServiceInstance stub adapter
    :type stub_adapter: SoapStubAdapter
    :param disable_ssl_verification: A flag used to skip ssl certificate
        verification (default is False)
    :type disable_ssl_verification: bool
    :returns: A VMware Storage Policy Service content object
    :rtype: ServiceContent
    """

    if disable_ssl_verification:
        import ssl
        if hasattr(ssl, '_create_unverified_context'):
            ssl_context = ssl._create_unverified_context()
        else:
            ssl_context = None
    else:
        ssl_context = None

    VmomiSupport.GetRequestContext()["vcSessionCookie"] = \
        stub_adapter.cookie.split('"')[1]
    hostname = stub_adapter.host.split(":")[0]
    pbm_stub = SoapStubAdapter(
        host=hostname,
        version="pbm.version.version1",
        path="/pbm/sdk",
        poolSize=0,
        sslContext=ssl_context)
    pbm_si = pbm.ServiceInstance("ServiceInstance", pbm_stub)
    pbm_content = pbm_si.RetrieveContent()
    return pbm_content


def get_storage_profiles(profile_manager, ref):
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
    profile_ids = profile_manager.PbmQueryAssociatedProfile(ref)
    if len(profile_ids) > 0:
        profiles = profile_manager.PbmRetrieveContent(profileIds=profile_ids)
        return profiles
    return profiles


def show_storage_profile_capabilities(capabilities):
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


def show_storage_profile(profiles):
    """Print vmware storage policy profile

    :param profiles: A list of VMware Storage Policy profiles
    :type profiles: pbm.profile.Profile[]
    :returns: None
    """

    for profile in profiles:
        print("Name: {}{}{} ".format(BColors.OKGREEN,
                                     profile.name,
                                     BColors.ENDC))
        print("ID: {} ".format(profile.profileId.uniqueId))
        print("Description: {} ".format(profile.description))
        if hasattr(profile.constraints, 'subProfiles'):
            subprofiles = profile.constraints.subProfiles
            for subprofile in subprofiles:
                print("RuleSetName: {} ".format(subprofile.name))
                capabilities = subprofile.capability
                show_storage_profile_capabilities(capabilities)


def search_vm_by_name(si, name, strict=False):
    """Search virtual machine by name

    :param si: A ServiceInstance managed object
    :type name: si
    :param name: A virtual machine name
    :type name: str
    :param strict: A flag used to set strict search method
        (default is False)
    :type strict: bool
    :returns: A virtual machine object
    :rtype: VirtualMachine
    """

    content = si.content
    root_folder = content.rootFolder
    obj_view = content.viewManager.CreateContainerView(root_folder, [vim.VirtualMachine], True)
    vm_list = obj_view.view
    obj_view.Destroy()
    obj = []
    for vm in vm_list:
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

    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.VM_NAME)
    parser.add_custom_argument('--strict', required=False, action='store_true',
                               help='Search strict virtual machine name matches')
    args = parser.get_args()
    si = service_instance.connect(args)

    pbm_content = pbm_connect(si._stub, args.disable_ssl_verification)
    pm = pbm_content.profileManager

    vm_list = search_vm_by_name(si, args.vm_name, args.strict)
    for vm in vm_list:
        print("Virtual machine name: {}{}{}".format(BColors.OKGREEN,
                                                    vm.name,
                                                    BColors.ENDC))
        pm_object_type = pbm.ServerObjectRef.ObjectType("virtualMachine")
        pm_ref = pbm.ServerObjectRef(key=vm._moId, objectType=pm_object_type)
        profiles = get_storage_profiles(pm, pm_ref)
        if len(profiles) > 0:
            print("Home Storage Profile:")
            show_storage_profile(profiles)

        print("\r\nVirtual Disk Storage Profile:")
        for device in vm.config.hardware.device:
            device_type = type(device).__name__
            if device_type == "vim.vm.device.VirtualDisk":
                pm_object_type = pbm.ServerObjectRef.ObjectType("virtualDiskId")
                pm_ref = pbm.ServerObjectRef(key="{}:{}".format(vm._moId, device.key), objectType=pm_object_type)
                profiles = get_storage_profiles(pm, pm_ref)
                if len(profiles) > 0:
                    print(device.deviceInfo.label)
                    show_storage_profile(profiles)
                    print("")
        print("")


if __name__ == "__main__":
    main()
