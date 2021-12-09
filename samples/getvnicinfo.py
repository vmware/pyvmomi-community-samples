#!/usr/bin/env python
#
# cpaggen - May 16 2015 - Proof of Concept (little to no error checks)
#  - rudimentary args parser
#  - get_hosts_portgroups() is quite slow; there is probably a better way
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pyVmomi import vim
from tools import cli, service_instance
import sys


def get_vm_hosts(content):
    print("Getting all ESX hosts ...")
    host_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.HostSystem],
                                                        True)
    hosts = list(host_view.view)
    host_view.Destroy()
    return hosts


def get_vms(content):
    print("Getting all VMs ...")
    vm_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                      [vim.VirtualMachine],
                                                      True)
    obj = [vm for vm in vm_view.view]
    vm_view.Destroy()
    return obj


def get_hosts_portgroups(hosts):
    print("Collecting portgroups on all hosts. This may take a while ...")
    host_pg_dict = {}
    for host in hosts:
        pgs = host.config.network.portgroup
        host_pg_dict[host] = pgs
        print("\tHost {} done.".format(host.name))
    print("\tPortgroup collection complete.")
    return host_pg_dict


def print_vminfo(vm):
    vm_power_state = vm.runtime.powerState
    print("Found VM:", vm.name + "(" + vm_power_state + ")")
    get_vm_nics(vm)


def get_vm_nics(vm):
    for dev in vm.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualEthernetCard):
            dev_backing = dev.backing
            port_group = None
            vlan_id = None
            v_switch = None
            if hasattr(dev_backing, 'port'):
                port_group_key = dev.backing.port.portgroupKey
                dvs_uuid = dev.backing.port.switchUuid
                try:
                    dvs = content.dvSwitchManager.QueryDvsByUuid(dvs_uuid)
                except Exception:
                    port_group = "** Error: DVS not found **"
                    vlan_id = "NA"
                    v_switch = "NA"
                else:
                    pg_obj = dvs.LookupDvPortGroup(port_group_key)
                    port_group = pg_obj.config.name
                    vlan_id = str(pg_obj.config.defaultPortConfig.vlan.vlanId)
                    v_switch = str(dvs.name)
            else:
                port_group = dev.backing.network.name
                vm_host = vm.runtime.host
                # global variable hosts is a list, not a dict
                host_pos = hosts.index(vm_host)
                view_host = hosts[host_pos]
                # global variable host_pg_dict stores portgroups per host
                pgs = host_pg_dict[view_host]
                for p in pgs:
                    if port_group in p.key:
                        vlan_id = str(p.spec.vlanId)
                        v_switch = str(p.spec.vswitchName)
            if port_group is None:
                port_group = 'NA'
            if vlan_id is None:
                vlan_id = 'NA'
            if v_switch is None:
                v_switch = 'NA'
            print('\t' + dev.deviceInfo.label + '->' + dev.macAddress +
                  ' @ ' + v_switch + '->' + port_group +
                  ' (VLAN ' + vlan_id + ')')


def main():
    global content, hosts, host_pg_dict
    parser = cli.Parser()
    args = parser.get_args()
    si = service_instance.connect(args)
    content = si.RetrieveContent()
    hosts = get_vm_hosts(content)
    host_pg_dict = get_hosts_portgroups(hosts)
    vms = get_vms(content)
    for vm in vms:
        print_vminfo(vm)


# Main section
if __name__ == "__main__":
    sys.exit(main())
