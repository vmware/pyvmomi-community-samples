#!/usr/bin/env python
"""
Copyright (c) 2023 VMware, Inc. All Rights Reserved.

Sample monitoring for changes in the MAC addresses of VMs.

The monitor uses the `PropertyCollector` API to detect changes in the MAC
addresses of VMs. The `PropertyCollector` is initialized with a `ContainerView`
of all VMs. As we can observe MAC addresses either from the virtual ethernet
cards or through the guest the property spec includes all VM virtual devices -
`config.hardware.device` and guest networks - `guest.net`. As ethernet cards
are only one of many possible virtual devices, we will receive spurious updates
related to other hardware. Also DHCP changes will update the `guest.net` values
even when the MAC and IP addresses do not change. To mitigate the spurious
updates the property collector output is filtered through a cache of currently
known values that only lets through real changes to MAC and IP addresses.

The code can be enhanced to run in a background executor and provide query
capability to query the cache as necessary.
"""


import time
from pyVmomi import vim, vmodl
from pyVim.connect import Disconnect
from tools import cli, service_instance

DEVICES_PROP_PATH = "config.hardware.device"
GUEST_NET_PROP_PATH = "guest.net"
NAME_PROP_PATH = "name"


class VMDetails:
    """
    Physical Networks Address details of a VM. Contains vm name and a map
    of device key to MAC address.
    """
    def __init__(self, vm_name: str, vnic: dict[int:str], guest_net: dict[str:list[str]]):
        """ Create a new VM Details
        vm_name: The name of the VM
        vm_mac_addresses: A map of device key to MAC address
        vnic: A map of device key to mac address
        guest_net: A map of mac address to ip addresses
        """
        self.vm_name = vm_name
        self.vnic = vnic
        self.guest_net = guest_net


class VmMacChangeListener:
    """ Listens for changes in the mac addresses of VMs """
    def update_vm(self, vm_id: str, vm_name: str,
                  vnic: dict[int:str], guest_net: dict[str:list[str]]):
        """ Update the VM details
        vm_id: The id of the VM
        vm_name: The name of the VM
        vnic: A map of device key to mac address
        guest_net: A map of mac address to ip addresses
        """
    def remove_vm(self, vm_id: str):
        """ Remove a VM from the list of VMs
        vm_id: The id of the VM
        """


class VmMacChangePrinter:
    """ Prints changes in the mac addresses of VMs """
    def update_vm(self, vm_id: str, vm_name: str,
                  vnic: dict[int:str], guest_net: dict[str:list[str]]):
        print(f"VM '{vm_name}' ({vm_id}) has mac addresses\
              \n\tVNICS: {vnic}\n\tGUEST_NET: {guest_net}")

    def remove_vm(self, vm_id: str):
        print(f"VM {vm_id} has been removed")


class VmMacCache(VmMacChangeListener):
    """
    This cache removes spurious updates to MAC and IP addresses. It listens for
    changes in the MAC addresses of VMs, updates the cache of VM Mac addresses
    when a real change occurs and notifies a nested VmMacChangeListener. The
    cache is a map of VM id to VMDetails.
    """
    def __init__(self, nested: VmMacChangeListener):
        """ Create a new VM Mac Change Cache
        nested: The next listener to notify of changes
        """
        self.vm_cache: dict[str, VMDetails] = {}
        self.nested = nested

    def update_vm(self, vm_id: str, vm_name: str,
                  vnic: dict[int:str], guest_net: dict[str:list[str]]):
        """ Update the VM details.
        vm_id: The id of the VM
        vm_name: The name of the VM
        vnic: A map of device key to mac address
        guest_net: A map of mac address to ip addresses
        """
        if vm_id in self.vm_cache:
            updated = False
            if vm_name and self.vm_cache[vm_id].vm_name != vm_name:
                self.vm_cache[vm_id].vm_name = vm_name
                updated = True
            if vnic and self.vm_cache[vm_id].vnic != vnic:
                self.vm_cache[vm_id].vnic = vnic
                updated = True
            if guest_net and self.vm_cache[vm_id].guest_net != guest_net:
                self.vm_cache[vm_id].guest_net = guest_net
                updated = True
            if updated:
                cached = self.vm_cache[vm_id]
                self.nested.update_vm(vm_id, cached.vm_name, cached.vnic, cached.guest_net)
        else:
            self.vm_cache[vm_id] = VMDetails(vm_name, vnic, guest_net)
            self.nested.update_vm(vm_id, vm_name, vnic, guest_net)

    def remove_vm(self, vm_id: str):
        """ Remove a VM from the list of VMs
        vm_id: The id of the VM
        """
        if vm_id in self.vm_cache:
            del self.vm_cache[vm_id]
            self.nested.remove_vm(vm_id)


def make_wait_options(max_wait_seconds: int = None, max_object_updates: int = None) -> \
            vmodl.query.PropertyCollector.WaitOptions:
    """
    Creates property collector wait options needed for WaitForUpdatesEx API.
    """
    wait_opts = vmodl.query.PropertyCollector.WaitOptions()

    if max_object_updates is not None:
        wait_opts.maxObjectUpdates = max_object_updates

    if max_wait_seconds is not None:
        wait_opts.maxWaitSeconds = max_wait_seconds

    return wait_opts


def create_view_filter(view: vim.view.View,
                       prop_spec: vmodl.query.PropertyCollector.PropertySpec) -> \
                        vmodl.query.PropertyCollector.FilterSpec:
    """
    Create a property collector filter spec based on a view object and a set of
    properties the caller wants to monitor.
    """
    traversal_spec = vmodl.query.PropertyCollector.TraversalSpec()
    traversal_spec.name = "traverseEntities"
    traversal_spec.path = "view"
    traversal_spec.skip = False
    traversal_spec.type = vim.view.ContainerView

    objectSpec = vmodl.query.PropertyCollector.ObjectSpec()
    objectSpec.obj = view
    objectSpec.skip = True
    objectSpec.selectSet = [traversal_spec]

    filter_spec = vmodl.query.PropertyCollector.FilterSpec()
    filter_spec.propSet = [prop_spec]
    filter_spec.objectSet = [objectSpec]

    return filter_spec


class VmMacChangeDetector:
    """ Detects changes in the MAC addresses of VMs from PropertyCollector updates. """
    def __init__(self, si: vim.ServiceInstance, listener: VmMacChangeListener,
                 max_wait_seconds: int = 10, max_object_updates: int = 100) -> None:
        """
        Create a new VM Mac Change Detector
        si: The Service Instance
        listener: The listener to notify of changes
        """
        self.si = si
        self.listener = listener
        self.max_wait_seconds = max_wait_seconds
        self.max_object_updates = max_object_updates
        self.version = ""
        self.pc = None
        self.view = None
        self.filter = None

    def monitor(self, seconds: int):
        """
        Monitor for changes in the mac addresses of VMs.
        seconds: number of seconds to monitor changes. 0 monitors indefinitely
        """
        if not self.pc:
            self._init_property_collector()

        wait_opts = make_wait_options(self.max_wait_seconds, self.max_object_updates)

        start = time.time()
        while seconds == 0 or time.time() - start < seconds:
            res = self.pc.WaitForUpdatesEx(self.version, wait_opts)
            if res is None:
                continue
            self.version = res.version
            for filter_set in res.filterSet:
                if filter_set.filter == self.filter:
                    self._process_updates(filter_set.objectSet)

    def close(self):
        """ Close the active objects """
        self.filter.DestroyPropertyFilter()
        self.view.DestroyView()
        self.pc.DestroyPropertyCollector()
        self.filter = None
        self.view = None
        self.pc = None

    def _init_property_collector(self):
        """ Initialise the PropertyCollector """
        self.pc = self.si.content.propertyCollector.CreatePropertyCollector()
        view_mgr = self.si.content.viewManager
        root_folder = self.si.content.rootFolder
        self.view = view_mgr.CreateContainerView(root_folder, [vim.VirtualMachine], True)

        prop_spec = vmodl.query.PropertyCollector.PropertySpec()
        prop_spec.type = vim.VirtualMachine
        prop_spec.pathSet = [NAME_PROP_PATH, GUEST_NET_PROP_PATH, DEVICES_PROP_PATH]

        filter_spec = create_view_filter(self.view, prop_spec)
        self.filter = self.pc.CreateFilter(filter_spec, False)
        self.version = ""

    def _process_updates(self, objects: list[vmodl.query.PropertyCollector.ObjectUpdate]):
        for obj_update in objects:
            # pylint: disable=W0212
            mo_id = obj_update.obj._GetMoId()
            if obj_update.kind == "leave":
                self.listener.remove_vm(mo_id)
                continue
            # 'enter' or 'modify'
            name = None
            vnic = None
            guest_net = None
            for change in obj_update.changeSet:
                if change.name == NAME_PROP_PATH:
                    if change.op != "assign":
                        print(f"WARN: Unexpected name change in {mo_id} \
                            {obj_update.obj.name}: {change.op}")
                        continue
                    name = change.val
                if change.name == GUEST_NET_PROP_PATH:
                    if change.op != "assign":
                        print(f"WARN: Unexpected net change in {mo_id} \
                              {obj_update.obj.name}: {change.op}")
                        continue
                    guest_net = self._get_guest_addresses(change.val)
                if change.name == DEVICES_PROP_PATH:
                    if change.op != "assign":
                        print(f"WARN: Unexpected device change in {mo_id} \
                              {obj_update.obj.name}: {change.op}")
                        continue
                    vnic = self._get_vnic_addresses(change.val)
            self.listener.update_vm(mo_id, name, vnic, guest_net)

    def _get_vnic_addresses(self, devices):
        vnic = {}
        for device in devices:
            if isinstance(device, vim.vm.device.VirtualEthernetCard) and \
                    device.key and device.macAddress:
                vnic[device.key] = device.macAddress
        return vnic

    def _get_guest_addresses(self, nics):
        guest_net = {}
        for nic in nics:
            if isinstance(nic, vim.vm.GuestInfo.NicInfo) and nic.macAddress:
                guest_net[nic.macAddress] = [ip.ipAddress for ip in nic.ipConfig.ipAddress] \
                                                if nic.ipConfig else []
        return guest_net

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def main():
    """
    Sample monitoring for changes in the MAC addresses of VMs.
    """
    parser = cli.Parser()
    parser.add_optional_arguments(cli.Argument.MINUTES)
    parser.add_custom_argument('--no_filter',
                               action="store_true",
                               default=False,
                               help='Remove the filtering cache.')
    args = parser.get_args()
    si = service_instance.connect(args)
    wait_seconds = int(args.minutes) * 60 if args.minutes else 60
    try:
        printer = VmMacChangePrinter()

        listener = printer if args.no_filter else VmMacCache(printer)

        with VmMacChangeDetector(si, listener) as detector:
            detector.monitor(wait_seconds)
    finally:
        Disconnect(si)


if __name__ == "__main__":
    main()
