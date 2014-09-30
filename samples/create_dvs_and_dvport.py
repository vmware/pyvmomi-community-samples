"""
Written by Reubenur Rahman
Github: https://github.com/rreubenur/

This code is released under the terms of the Apache 2
http://www.apache.org/licenses/LICENSE-2.0.html

Example script to create a Vsphere Distributed Virtual Switch

"""

import atexit
import getpass
from tools import cli
from tools import tasks
from pyVim import connect
from pyVmomi import vim, vmodl


def get_args():
    """Get command line args from the user.
    """
    parser = cli.build_arg_parser()
    parser.add_argument('-d', '--dvs_name',
                        required=True,
                        help='Name of the Distributed Virtual Switch '
                             'you want to create')

    parser.add_argument('-g', '--pg_name',
                        required=False,
                        action='store',
                        help='Name of the Distributed Port Group')

    parser.add_argument('-l', '--vlan_id',
                        required=False,
                        action='store',
                        help='VLAN ID')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password for host %s and user %s: ' %
                   (args.host, args.user))
    return args


def get_free_pnic(host):
    all_pnics = []
    used_pnics = []
    pnics = host.config.network.pnic
    for pnic in pnics:
        all_pnics.append(pnic.key)

    vswitches = host.config.network.vswitch
    for vswitch in vswitches:
        used_pnics += vswitch.pnic
    proxy_switches = host.config.network.proxySwitch
    for ps in proxy_switches:
        used_pnics += ps.pnic

    free_pnics = [nic for nic in all_pnics if nic not in used_pnics]
    if free_pnics:
        free_pnic = free_pnics.pop()
    else:
        print "Esxi host doesn't have any free Physical NIC"
        "to attach with the DV switch"
        return None

    return free_pnic[free_pnic.rfind('-') + 1:]


def add_dv_port_groups(si, pg_name, dv_switch, vlan_id):
    dv_pg_spec = vim.dvs.DistributedVirtualPortgroup.ConfigSpec()
    dv_pg_spec.name = pg_name
    dv_pg_spec.type = vim.dvs.DistributedVirtualPortgroup. \
    PortgroupType.earlyBinding
    dv_pg_spec.autoExpand = True
    dv_pg_spec.defaultPortConfig = vim.dvs. \
    VmwareDistributedVirtualSwitch.VmwarePortConfigPolicy()
    dv_pg_spec.defaultPortConfig.securityPolicy = \
    vim.dvs.VmwareDistributedVirtualSwitch.SecurityPolicy()

    dv_pg_spec.defaultPortConfig.vlan = \
    vim.dvs.VmwareDistributedVirtualSwitch.VlanIdSpec()
    dv_pg_spec.defaultPortConfig.vlan.vlanId = int(vlan_id)
    dv_pg_spec.defaultPortConfig.securityPolicy. \
    allowPromiscuous = vim.BoolPolicy(value=True)
    dv_pg_spec.defaultPortConfig.securityPolicy. \
    forgedTransmits = vim.BoolPolicy(value=True)
    dv_pg_spec.defaultPortConfig.securityPolicy.macChanges = \
    vim.BoolPolicy(value=False)
    dv_pg_spec.defaultPortConfig.vlan.inherited = False

    dv_pg_spec.defaultPortConfig.securityPolicy.inherited = False

    task = dv_switch.AddDVPortgroup_Task([dv_pg_spec])
    tasks.wait_for_tasks(si, [task])
    print "Successfully added port group"


def create_dvSwitch(si, content, network_folder, hosts, dvs_name):
    dvs_host_configs = []
    api_versions = []
    dvs_create_spec = vim.DistributedVirtualSwitch.CreateSpec()
    dvs_config_spec = vim.DistributedVirtualSwitch.ConfigSpec()
    dvs_config_spec.name = dvs_name
    #Max DV Ports per Vcenter
    dvs_config_spec.maxPorts = 30000
    dvs_config_spec.uplinkPortPolicy = \
    vim.DistributedVirtualSwitch.NameArrayUplinkPortPolicy()
    dvs_config_spec.uplinkPortPolicy.uplinkPortName = ['dvUplink']
    for host in hosts:
        dvs_host_config = vim.dvs.HostMember.ConfigSpec()
        dvs_host_config.operation = vim.ConfigSpecOperation.add
        dvs_host_config.backing = vim.dvs.HostMember.PnicBacking()
        pnic_device = get_free_pnic(host)
        if pnic_device is None:
            continue
        pnic_spec = vim.dvs.HostMember.PnicSpec(pnicDevice=pnic_device)
        dvs_host_config.backing.pnicSpec = [pnic_spec]
        dvs_host_config.host = host
        dvs_host_configs.append(dvs_host_config)
        dvs_config_spec.host = dvs_host_configs
        api_versions.append(host.config.product.apiVersion)
    dvs_create_spec.configSpec = dvs_config_spec
    dvs_create_spec.productInfo = vim.dvs. \
    ProductSpec(version=min(api_versions) + '.0')
    print "Creating DVS ...", dvs_name
    task = network_folder.CreateDVS_Task(dvs_create_spec)
    tasks.wait_for_tasks(si, [task])
    #NOTE: This is not required if wait_for_tasks returns
    #task.info.result
    container = content.viewManager.CreateContainerView(
    content.rootFolder, [vim.DistributedVirtualSwitch], True)
    for view in container.view:
        if view.name == dvs_name:
            return view


def main():
    """
    Simple command-line program for creating DVS and DV Port Group
    """

    args = get_args()

    try:
        service_instance = connect.SmartConnect(host=args.host,
                                                user=args.user,
                                                pwd=args.password,
                                                port=int(args.port))

        atexit.register(connect.Disconnect, service_instance)
        content = service_instance.RetrieveContent()

        if not service_instance:
            raise SystemExit("Unable to connect to host with supplied info.")

        for child in content.rootFolder.childEntity:
            if hasattr(child, 'hostFolder'):
                datacenter = child
                break
        network_folder = datacenter.networkFolder
        obj_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.HostSystem],
                                                        True)
        hosts = obj_view.view

        dv_switch = create_dvSwitch(service_instance, content, network_folder,
                                    hosts, args.dvs_name)

        add_dv_port_groups(service_instance, args.pg_name, dv_switch,
                           args.vlan_id)
    except vmodl.MethodFault as error:
        print "Caught vmodl fault : " + error.msg
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
