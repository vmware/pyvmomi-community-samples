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

import atexit
import re
import tools.cli as cli

from pyVmomi import pbm, vim, VmomiSupport, SoapStubAdapter
from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect


def get_args():
    """Supports the command-line arguments listed below.
    """
    parser = cli.build_arg_parser()
    parser.description = 'Set VM Home or Virtual Disk Storage Policies'
    parser.add_argument('-v', '--vm_name',
                        required=True,
                        action='store',
                        metavar='string',
                        help='Get virtual machine by name')
    parser.add_argument('--strict',
                        required=False,
                        action='store_true',
                        help='Search strict virtual machine name matches')
    parser.add_argument('--set_vm_home',
                        required=False,
                        action='store_true',
                        help='Set the specified policy for vm home.')
    parser.add_argument('--virtual_disk_number',
                        required=False,
                        nargs='+',
                        metavar='int',
                        help='The sequence numbers of the virtual disks for which \
                              the specified policy should be set. \
                              Space as delimiter.')
    parser.add_argument('--storage_policy_name',
                        required=True,
                        action='store',
                        metavar='string',
                        help='The name of the storage policy to be set for VM \
                              Home or Virtual Disk')
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


def CheckStorageProfileAssociated(profileManager, ref, name):
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

    profileIds = profileManager.PbmQueryAssociatedProfile(ref)
    if len(profileIds) > 0:
        profiles = profileManager.PbmRetrieveContent(profileIds=profileIds)
        for profile in profiles:
            if profile.name == name:
                return True
    return False


def SearchStorageProfileByName(profileManager, name):
    """Search vmware storage policy profile by name

    :param profileManager: A VMware Storage Policy Service manager object
    :type profileManager: pbm.profile.ProfileManager
    :param name: A VMware Storage Policy profile name
    :type name: str
    :returns: A VMware Storage Policy profile
    :rtype: pbm.profile.Profile
    """

    profileIds = profileManager.PbmQueryProfile(
        resourceType=pbm.profile.ResourceType(resourceType="STORAGE"),
        profileCategory="REQUIREMENT"
    )
    if len(profileIds) > 0:
        storageProfiles = profileManager.PbmRetrieveContent(
            profileIds=profileIds)

    for storageProfile in storageProfiles:
        if storageProfile.name == name:
            return storageProfile


def SetVMStorageProfile(vm, profile):
    """Set vmware storage policy profile to VM Home

    :param vm: A virtual machine object
    :type vm: VirtualMachine
    :param profile: A VMware Storage Policy profile
    :type profile: pbm.profile.Profile
    :returns: None
    """

    spec = vim.vm.ConfigSpec()
    profileSpecs = []
    profileSpec = vim.vm.DefinedProfileSpec()
    profileSpec.profileId = profile.profileId.uniqueId
    profileSpecs.append(profileSpec)
    spec.vmProfile = profileSpecs
    vm.ReconfigVM_Task(spec)


def SetVirtualDiskStorageProfile(vm, hardwareDevice, profile):
    """Set vmware storage policy profile to Virtual Disk

    :param vm: A virtual machine object
    :type vm: VirtualMachine
    :param hardwareDevice: A virtual disk object
    :type hardwareDevice: VirtualDevice
    :param profile: A VMware Storage Policy profile
    :type profile: pbm.profile.Profile
    :returns: None
    """

    spec = vim.vm.ConfigSpec()
    deviceSpecs = []
    profileSpecs = []
    profileSpec = vim.vm.DefinedProfileSpec()
    profileSpec.profileId = profile.profileId.uniqueId
    profileSpecs.append(profileSpec)

    deviceSpec = vim.vm.device.VirtualDeviceSpec()
    deviceSpec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
    deviceSpec.device = hardwareDevice
    deviceSpec.profile = profileSpecs
    deviceSpecs.append(deviceSpec)
    spec.deviceChange = deviceSpecs
    vm.ReconfigVM_Task(spec)


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
        raise SystemExit('Unable to connect to host with supplied info.')

    vdNumber = args.virtual_disk_number
    policyName = args.storage_policy_name

    pbm_content = PbmConnect(serviceInstance._stub,
                             args.disable_ssl_verification)
    pm = pbm_content.profileManager

    storageProfile = SearchStorageProfileByName(pm, policyName)
    if not storageProfile:
        raise SystemExit('Unable to find storage profile with name '
                         '{}{}{}.'.format(bcolors.FAIL,
                                          policyName,
                                          bcolors.ENDC))

    vm_list = SearchVMByName(serviceInstance, args.vm_name, args.strict)
    for vm in vm_list:
        pmObjectType = pbm.ServerObjectRef.ObjectType("virtualMachine")
        pmRef = pbm.ServerObjectRef(key=vm._moId,
                                    objectType=pmObjectType)
        print('\r\nVirtual machine name: {}{}{}'.format(bcolors.OKGREEN,
                                                        vm.name,
                                                        bcolors.ENDC))

        # The implementation of idempotency for the operation of the storage
        # policy assignment for VM Home
        if args.set_vm_home:
            if not CheckStorageProfileAssociated(pm,
                                                 pmRef,
                                                 policyName):
                print('Set VM Home policy: '
                      '{}{}{}'.format(bcolors.OKGREEN,
                                      policyName,
                                      bcolors.ENDC))

                try:
                    SetVMStorageProfile(vm, storageProfile)
                except Exception as exc:
                    print('VM reconfiguration task error: '
                          '{}{}{}'.format(bcolors.FAIL,
                                          exc,
                                          bcolors.ENDC))
            else:
                print('Set VM Home policy: Nothing to do')

        if vdNumber:
            for device in vm.config.hardware.device:
                deviceType = type(device).__name__
                if deviceType == "vim.vm.device.VirtualDisk" and \
                   re.search('Hard disk (.+)',
                             device.deviceInfo.label).group(1) in vdNumber:
                    pmObjectType = \
                        pbm.ServerObjectRef.ObjectType("virtualDiskId")
                    pmRef = pbm.ServerObjectRef(key="{}:{}".format(vm._moId,
                                                                   device.key),
                                                objectType=pmObjectType)

                    # The implementation of idempotency for the operation
                    # of the storage policy assignment for virtual disk
                    if not CheckStorageProfileAssociated(pm,
                                                         pmRef,
                                                         policyName):
                        print('Set {} policy: '
                              '{}{}{}'.format(device.deviceInfo.label,
                                              bcolors.OKGREEN,
                                              policyName,
                                              bcolors.ENDC))
                        try:
                            SetVirtualDiskStorageProfile(vm,
                                                         device,
                                                         storageProfile)
                        except Exception as exc:
                            print('Virtual disk reconfiguration task error: '
                                  '{}{}{}'.format(bcolors.FAIL,
                                                  exc,
                                                  bcolors.ENDC))
                    else:
                        print('Set {} policy: Nothing to do'.format(
                            device.deviceInfo.label))


if __name__ == "__main__":
    main()
