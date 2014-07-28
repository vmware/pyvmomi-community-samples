import atexit
from getpass import getpass

from pyVim import connect

"""
This module overlays the pyVmomi library to make its use in a
python shell or short program more enjoyable.
Starting point is instantiating a vCenter Host (VVC) in order
to get all VMs.
"""


class VVC(object):
    """
    A vCenter host.
    """

    def __init__(self, hostname):
        """
        Creates a VVC instance.

        - `hostname` (str) is the name of the vCenter host.
        """
        self.hostname = hostname

    def connect(self, username, password=None):
        """
        Connects to the vCenter host encapsulated by this VVC instance.

        - `username` (str) is the username to use for authentication.
        - `password` (str) is the password to use for authentication.
          If the password is not specified, a getpass prompt will be used.
        """
        if not password:
            password = getpass("Password for {0}: ".format(self.hostname))
        self.service_instance = connect.SmartConnect(host=self.hostname,
                                                     user=username,
                                                     pwd=password,
                                                     port=443)
        atexit.register(connect.Disconnect, self.service_instance)

    def get_first_level_of_vm_folders(self):
        content = self.service_instance.RetrieveContent()
        children = content.rootFolder.childEntity
        for child in children:
            if hasattr(child, "vmFolder"):
                yield child.vmFolder

    def get_all_vms(self):
        """
        Returns a generator over all VMs known to this vCenter host.
        """
        for folder in self.get_first_level_of_vm_folders():
            for vm in get_all_vms_in_folder(folder):
                yield vm


class ESX(object):
    """
    An ESX instance.
    """

    def __init__(self, raw_esx):
        self.raw_esx = raw_esx
        self.name = raw_esx.name

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return int("".join((str(ord(c)) for c in self.name)))

    def __getattr__(self, attribute):
        return getattr(self.raw_esx, attribute)

    def get_number_of_cores(self):
        """
        Returns the number of CPU cores (type long) on this ESX.
        """
        resources_on_esx = self.raw_esx.licensableResource.resource
        for resource in resources_on_esx:
            if resource.key == "numCpuCores":
                return resource.value
        message = "{0} has no resource numCpuCores.\n Available resources: {1}"
        raise RuntimeError(message.format(self.name, resources_on_esx))


class VM(object):
    """
    A virtual machine.
    """

    def __init__(self, raw_vm):
        self.raw_vm = raw_vm
        self.name = raw_vm.name

    def __getattr__(self, attribute):
        return getattr(self.raw_vm, attribute)

    def get_first_network_interface_matching(self, predicate):
        """
        Returns the first network interface of this VM that matches the given
        predicate.

        - `predicate` (callable) is a function that takes a network and returns
          True (return this network) or False (skip this network).
        """
        for network in self.raw_vm.network:
            if predicate(network):
                return network
        return None

    def get_esx_host(self):
        return ESX(self.raw_vm.runtime.host)


def get_all_vms_in_folder(folder):
    vm_or_folders = folder.childEntity
    for vm_or_folder in vm_or_folders:
        if hasattr(vm_or_folder, "childEntity"):
            # it's still a folder, look deeper
            for vm in get_all_vms_in_folder(vm_or_folder):
                yield vm  # it's now a VM
        else:
            yield VM(vm_or_folder)  # it's a VM
