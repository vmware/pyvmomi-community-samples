#!/usr/bin/env python
"""
Written by Vadim Aleksandrov
Github: https://github.com/verdel
Email: valeksandrov@me.com

This code has been released under the terms of the Apache-2.0 license
http://opensource.org/licenses/Apache-2.0

Example of using Storage Policy
Based Management (SPBM) API to set VM Home
and Virtual Disk Storage Policies

Thanks to William Lam (https://github.com/lamw) for ideas from
the script list_vm_storage_policy.py
"""

import re
from tools import cli, service_instance
from pyVmomi import pbm, vim, VmomiSupport, SoapStubAdapter


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


def check_storage_profile_associated(profile_manager, ref, name):
    """Get name of VMware Storage Policy profile associated with
        the specified entities

    :param profileManager: A VMware Storage Policy Service manager object
    :type profileManager: pbm.profile.ProfileManager
    :param ref: A server reference to a virtual machine, virtual disk,
        or datastore
    :type ref: pbm.ServerObjectRef
    :param name: A VMware Storage Policy profile name
    :type name: str
    :returns: True if VMware Storage Policy profile with the specified
        name associated with the specified entities
    :rtype: bool
    """

    profile_ids = profile_manager.PbmQueryAssociatedProfile(ref)
    if len(profile_ids) > 0:
        profiles = profile_manager.PbmRetrieveContent(profileIds=profile_ids)
        for profile in profiles:
            if profile.name == name:
                return True
    return False


def search_storage_profile_by_name(profile_manager, name):
    """Search vmware storage policy profile by name

    :param profileManager: A VMware Storage Policy Service manager object
    :type profileManager: pbm.profile.ProfileManager
    :param name: A VMware Storage Policy profile name
    :type name: str
    :returns: A VMware Storage Policy profile
    :rtype: pbm.profile.Profile
    """

    profile_ids = profile_manager.PbmQueryProfile(
        resourceType=pbm.profile.ResourceType(resourceType="STORAGE"),
        profileCategory="REQUIREMENT"
    )
    if len(profile_ids) > 0:
        storage_profiles = profile_manager.PbmRetrieveContent(
            profileIds=profile_ids)

    for storageProfile in storage_profiles:
        if storageProfile.name == name:
            return storageProfile


def set_vm_storage_profile(vm, profile):
    """Set vmware storage policy profile to VM Home

    :param vm: A virtual machine object
    :type vm: VirtualMachine
    :param profile: A VMware Storage Policy profile
    :type profile: pbm.profile.Profile
    :returns: None
    """

    spec = vim.vm.ConfigSpec()
    profile_specs = []
    profile_spec = vim.vm.DefinedProfileSpec()
    profile_spec.profileId = profile.profileId.uniqueId
    profile_specs.append(profile_spec)
    spec.vmProfile = profile_specs
    vm.ReconfigVM_Task(spec)


def set_virtual_disk_storage_profile(vm, hardware_device, profile):
    """Set vmware storage policy profile to Virtual Disk

    :param vm: A virtual machine object
    :type vm: VirtualMachine
    :param hardware_device: A virtual disk object
    :type hardware_device: VirtualDevice
    :param profile: A VMware Storage Policy profile
    :type profile: pbm.profile.Profile
    :returns: None
    """

    spec = vim.vm.ConfigSpec()
    device_specs = []
    profile_specs = []
    profile_spec = vim.vm.DefinedProfileSpec()
    profile_spec.profileId = profile.profileId.uniqueId
    profile_specs.append(profile_spec)

    device_spec = vim.vm.device.VirtualDeviceSpec()
    device_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
    device_spec.device = hardware_device
    device_spec.profile = profile_specs
    device_specs.append(device_spec)
    spec.deviceChange = device_specs
    vm.ReconfigVM_Task(spec)


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
            if vm.name == name:
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
    parser.add_required_arguments(cli.Argument.VM_NAME, cli.Argument.STORAGE_POLICY_NAME)
    parser.add_custom_argument('--strict', required=False, action='store_true',
                               help='Search strict virtual machine name matches')
    parser.add_custom_argument('--set_vm_home', required=False, action='store_true',
                               help='Set the specified policy for vm home.')
    parser.add_custom_argument('--virtual_disk_number', required=False, nargs='+', metavar='int',
                               help='The sequence numbers of the virtual disks for which the specified policy should be'
                                    ' set. Space as delimiter.')
    args = parser.get_args()
    si = service_instance.connect(args)

    vd_number = args.virtual_disk_number
    policy_name = args.storage_policy_name

    pbm_content = pbm_connect(si._stub, args.disable_ssl_verification)
    pm = pbm_content.profileManager

    storage_profile = search_storage_profile_by_name(pm, policy_name)
    if not storage_profile:
        raise SystemExit('Unable to find storage profile with name '
                         '{}{}{}.'.format(BColors.FAIL, policy_name, BColors.ENDC))

    vm_list = search_vm_by_name(si, args.vm_name, args.strict)
    for vm in vm_list:
        pm_object_type = pbm.ServerObjectRef.ObjectType("virtualMachine")
        pm_ref = pbm.ServerObjectRef(key=vm._moId, objectType=pm_object_type)
        print('\r\nVirtual machine name: {}{}{}'.format(BColors.OKGREEN,
                                                        vm.name,
                                                        BColors.ENDC))

        # The implementation of idempotency for the operation of the storage
        # policy assignment for VM Home
        if args.set_vm_home:
            if not check_storage_profile_associated(pm, pm_ref, policy_name):
                print('Set VM Home policy: '
                      '{}{}{}'.format(BColors.OKGREEN,
                                      policy_name,
                                      BColors.ENDC))

                try:
                    set_vm_storage_profile(vm, storage_profile)
                except Exception as exc:
                    print('VM reconfiguration task error: '
                          '{}{}{}'.format(BColors.FAIL,
                                          exc,
                                          BColors.ENDC))
            else:
                print('Set VM Home policy: Nothing to do')

        if vd_number:
            for device in vm.config.hardware.device:
                device_type = type(device).__name__
                if device_type == "vim.vm.device.VirtualDisk" and \
                   re.search('Hard disk (.+)',
                             device.deviceInfo.label).group(1) in vd_number:
                    pm_object_type = \
                        pbm.ServerObjectRef.ObjectType("virtualDiskId")
                    pm_ref = pbm.ServerObjectRef(key="{}:{}".format(vm._moId, device.key), objectType=pm_object_type)

                    # The implementation of idempotency for the operation
                    # of the storage policy assignment for virtual disk
                    if not check_storage_profile_associated(pm, pm_ref, policy_name):
                        print('Set {} policy: '
                              '{}{}{}'.format(device.deviceInfo.label,
                                              BColors.OKGREEN,
                                              policy_name,
                                              BColors.ENDC))
                        try:
                            set_virtual_disk_storage_profile(vm, device, storage_profile)
                        except Exception as exc:
                            print('Virtual disk reconfiguration task error: '
                                  '{}{}{}'.format(BColors.FAIL,
                                                  exc,
                                                  BColors.ENDC))
                    else:
                        print('Set {} policy: Nothing to do'.format(
                            device.deviceInfo.label))


if __name__ == "__main__":
    main()
