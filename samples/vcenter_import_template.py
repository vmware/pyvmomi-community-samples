#!/usr/bin/env python
# This is sort of a template script for most operations that might have to
# recursively traverse the vcenter objects looking for something.
# For example importing data from vcenter into another system. 
#
# by Stefan Midjich <swehack@gmail.com>
#
# See comments further down in the code to understand more.
# It's important to know the object structure of your vcenter so look into
# your own MOB first. It's found at https://10.11.12.13/mob on your vcenter
# server.
# In the MOB you have several paths to take.
#   * content.rootFolder.childEntity - Datacenters
#   * Datacenter.hostFolder - Clusters
#   * Datacenter.vmFolder - VM Folders
#
# VM Folders is the structure you see in the VC client under VMs and
# Templates.
# Clusters will lead you to hosts but you can also see which host a VM is on
# through VM Folders and the actual VirtualMachine object.
#
# See help by running ./pyvmomi_example1.py --help
#
# Config files read are:
#   * ./import_defaults.cfg
#   * ./import_local.cfg
#
# Config file example:
#
# [vcenter]
# hostname = 10.11.12.13
# username = svc_vmware
# password = secrets
# port = 443

from __future__ import print_function

import atexit
from sys import exit, stderr
from urllib import unquote
from argparse import ArgumentParser
from ConfigParser import ConfigParser

from pyVim.connect import SmartConnect, Disconnect

config = ConfigParser()
config.readfp(open('pyvmomi_defaults.cfg'))
config.read(['./pyvmomi_local.cfg'])

parser = ArgumentParser(
    description='List all VMs on a specific ESX host',
    epilog='Example: ./get_all_vms.py -c my_pyvmomi.cfg'
)

parser.add_argument(
    '-c', '--configuration',
    type=file,
    dest='config_file',
    help='Additional configuration options'
)

parser.add_argument(
    '-v', '--verbose',
    action='count',
    default=False,
    dest='verbose',
    help='Verbose output, use more v\'s to increase level'
)


# Recursively traverse vm entities from vcenter (datacenters, clusters,
# folders, vms)
def traverse_entities(vc_root, depth=1):
    # Parse cli args here for access to verbose flag
    args = parser.parse_args()

    # Recursive depth limit
    maxdepth = 16

    if depth > maxdepth:
        if args.verbose:
            print(
                'Reached max recursive depth, bailing out like a banker',
                file=stderr
            )
        return

    # This stores the name of the class, identifies the type of objects we're
    # dealing with.
    object_type = vc_root.__class__.__name__

    # There are 6 if blocks here that can process one type of object each.
    # After them the final object is processed which is a VirtualMachine.

    # Datacenter
    if object_type == 'vim.Datacenter':
        datacenter_name = unquote(vc_root.name)

        # This is where you take action on Datacenters

        # First recurse through clusters in Datacenter.hostFolder
        for _entity in vc_root.hostFolder.childEntity:
            traverse_entities(_entity, depth+1)

        # Continue recursively to subfolders in Datacenter.vmFolder
        for _entity in vc_root.vmFolder.childEntity:
            traverse_entities(_entity, depth+1)
        return

    # Clusters
    if object_type == 'vim.ClusterComputeResource':
        cluster_name = unquote(vc_root.name)

        # This is where you take action on Clusters
        # For example list all their ESX hosts.

        # Loop through hosts in this cluster in Cluster.host
        for _entity in vc_root.host:
            traverse_entities(_entity, depth+1)
        return

    # This is an ESX host under a datacenter, weirdly enough...
    if object_type == 'vim.ComputeResource':
        resource_name = unquote(vc_root.name)

        # Take action on ESX hosts under datacenters, that happen to be called
        # ComputeResource. 

        # Loop through member ESX hosts of this resource
        for _entity in vc_root.host:
            traverse_entities(_entity, depth+1)
        return

    # ESX Hosts
    if object_type == 'vim.HostSystem':
        host_name = unquote(vc_root.name)

        # Here you can take action on ESX hosts, for example list all their
        # VMs.
        #print('Searching ESX host {0}'.format(host_name))

        ## Loop through VMs on this host
        #for _entity in vc_root.vm:
        #    traverse_entities(_entity, depth+1)

        #print('Finished searching ESX host {0} for VMs'.format(host_name))
        # End of demonstration code.

        return

    # Folders
    if object_type == 'vim.Folder':
        folder_name = unquote(vc_root.name)

        # Take action on VM Folders

        # Traverse subfolders of this folder
        for _entity in vc_root.childEntity:
            traverse_entities(_entity, depth+1)
        return

    # Virtual Appliances
    if object_type == 'vim.VirtualApp':
        vapp_name = unquote(vc_root.name)

        # Take action on Virtual Appliances

        for _entity in vc_root.vm:
            traverse_entities(_entity, depth+1)
        return

    # Further objects should only be Virtual Machines, skip and report any
    # unknown objects.
    if object_type != 'vim.VirtualMachine':
        if args.verbose:
            print('{0}: Found unknown object, skipping it'.format(
                object_type
            ))
        return

    # From here on a VM is processed, you can get lots of information about
    # them from vcenter and from guest tools, if they're installed. See the
    # mob for more info.
    vm = vc_root
    vm_name = unquote(vm.name)

    #print('Found VM {0}'.format(vm_name))

    # The following code gathers information about the VM from various
    # attributes of the VirtualMachine object in vcenter.
    if hasattr(vm, 'runtime'):
        runtime = vm.runtime

        # Get cluster name of VM
        try:
            cluster_name = runtime.host.parent.name
        except AttributeError:
            cluster_name = ''

        # Get last VM power state, this is only interesting because newly
        # imported VMs will lack guest info like IP and networks if they're
        # powered off at import.
        try:
            power_state = str(runtime.powerState)
        except AttributeError:
            power_state = ''


def main():
    args = parser.parse_args()

    # Read additional configuration file provided through cli arguments
    if args.config_file:
        config.readfp(args.config_file)

    # Connect to vcenter
    try:
        si = SmartConnect(
            host=config.get('vcenter', 'hostname'),
            user=config.get('vcenter', 'username'),
            pwd=config.get('vcenter', 'password'),
            port=int(config.get('vcenter', 'port'))
        )
    except Exception as e:
        print(
            'Could not connect to vcenter server: {0}'.format(
                str(e)
            ), file=stderr
        )
        exit(-1)

    # On exit of script, run Disconnect method to disconnect from vcenter
    atexit.register(Disconnect, si)

    # Main content object from vcenter
    content = si.RetrieveContent()

    # Loop through each parent entity recursively
    for child in content.rootFolder.childEntity:
        traverse_entities(child)

if __name__ == '__main__':
    main()
