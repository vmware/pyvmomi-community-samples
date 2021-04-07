#!/usr/bin/env python
# William Lam
# www.virtuallyghetto.com

"""
vSphere Python SDK program for updating ESXi Advanced Settings

Usage:
    python update_esxi_advanced_settings.py -s 192.168.1.200 \
    -u 'administrator@vsphere.local' \
    -p VMware1! -c VSAN-Cluster -k VSAN.ClomRepairDelay -v 120
"""

from pyVmomi import vim, vmodl
from tools import cli, service_instance, pchelper


def main():
    """
   Simple command-line program demonstrating how to update
   ESXi Advanced Settings
   """

    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.CLUSTER_NAME)
    parser.add_custom_argument('--key', required=True, action='store',
                               help='Name of ESXi Advanced Setting to update')
    parser.add_custom_argument('--value', required=True, action='store',
                               help='Value of the ESXi Advanced Setting to update')
    args = parser.get_args()
    try:
        si = service_instance.connect(args)

        content = si.RetrieveContent()

        cluster = pchelper.get_obj(content, [vim.ClusterComputeResource], args.cluster_name)

        hosts = cluster.host
        for host in hosts:
            option_manager = host.configManager.advancedOption
            option = vim.option.OptionValue(key=args.key,
                                            value=int(args.value))
            print("Updating %s on ESXi host %s "
                  "with value of %s" % (args.key, host.name, args.value))
            if option_manager.UpdateOptions(changedValue=[option]):
                print("Settings updated!")

    except vmodl.MethodFault as ex:
        print("Caught vmodl fault : " + ex.msg)
        return -1
    except Exception as ex:
        print("Caught exception : " + str(ex))
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
