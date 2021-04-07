#!/usr/bin/env python

"""
Written by David Martinez
Github: https://github.com/dx0xm

Script to list all portgroup vlan on existing or selected dvswitch
This is for demonstration and reference purposes.
Testing ok in Single datacenter, multiple dvswitch instances
Based on getvnicinfo.py and py-vminfo.py

To improve:
Error handling
"""

from pyVmomi import vim
from tools import cli, service_instance, pchelper


def main():
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.DATACENTER_NAME)
    parser.add_custom_argument('--dvswitch-name', required=False,
                               help='name of the dvswitch', default='all')
    args = parser.get_args()
    si = service_instance.connect(args)

    content = si.RetrieveContent()

    datacenter = pchelper.get_obj(content, [vim.Datacenter], args.datacenter_name)

    if datacenter is None:
        print("Failed to find the datacenter %s" % args.datacenter_name)
        return 0

    if args.dvswitch_name == 'all':
        dvs_lists = pchelper.get_all_obj(
            content, [vim.DistributedVirtualSwitch], folder=datacenter.networkFolder)
    else:
        dvsn = pchelper.search_for_obj(content, [vim.DistributedVirtualSwitch], args.dvswitch_name)
        if dvsn is None:
            print("Failed to find the dvswitch %s" % args.dvswitch_name)
            return 0
        dvs_lists = [dvsn]

    print('Datacenter Name'.ljust(40)+' :', args.datacenter_name)
    for dvs in dvs_lists:
        print(40*'#')
        print('Dvswitch Name'.ljust(40)+' :', dvs.name)
        print(40*'#')
        for dvs_pg in dvs.portgroup:
            vlan_info = dvs_pg.config.defaultPortConfig.vlan
            vlan_spec = vim.dvs.VmwareDistributedVirtualSwitch.TrunkVlanSpec
            if isinstance(vlan_info, vlan_spec):
                vlanlist = []
                for item in vlan_info.vlanId:
                    if item.start == item.end:
                        vlanlist.append(str(item.start))
                    else:
                        vlanlist.append(str(item.start)+'-'+str(item.end))
                vlan_id = " | Trunk | vlan id: " + ','.join(vlanlist)
            else:
                vlan_id = " | vlan id: " + str(vlan_info.vlanId)
            print(dvs_pg.name.ljust(40) + vlan_id)
    return 0


if __name__ == "__main__":
    main()
