#!/usr/bin/env python
"""
Written by Nathan Prziborowski
Github: https://github.com/prziborowski

This code is released under the terms of the Apache 2
http://www.apache.org/licenses/LICENSE-2.0.html

Simple example for getting the vMotion/relocate events of a VM.
There are additional filters for time that I didn't include as I
didn't want to add time parsing complications.

"""
import re
from pyVmomi import vim
from tools import cli, service_instance

__author__ = 'prziborowski'

def get_dc(si, name):
    """
    Get a datacenter by its name.
    """
    for dc in si.content.rootFolder.childEntity:
        if dc.name == name:
            return dc
    raise Exception('Failed to find datacenter named %s' % name)

def main():
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.VM_NAME, cli.Argument.DATACENTER_NAME)
    parser.add_custom_argument('--filterUsers', help="Comma-separated list of users to filter on")
    parser.add_custom_argument('--filterSystemUser', action='store_true',
                                        help="Filter system user, defaults to false.")
    args = parser.get_args()
    serviceInstance = service_instance.connect(args)

    if args.datacenter_name:
        dc = get_dc(serviceInstance, args.datacenter_name)
    else:
        dc = serviceInstance.content.rootFolder.childEntity[0]

    vm = serviceInstance.content.searchIndex.FindChild(dc.vmFolder, args.vm_name)
    if vm is None:
        raise Exception('Failed to find VM %s in datacenter %s' %
                        (dc.name, args.vm_name))
    byEntity = vim.event.EventFilterSpec.ByEntity(entity=vm, recursion="self")
    ids = ['VmRelocatedEvent', 'DrsVmMigratedEvent', 'VmMigratedEvent']
    filterSpec = vim.event.EventFilterSpec(entity=byEntity, eventTypeId=ids)

    # Optionally filter by users
    userList = []
    if args.filterUsers:
        userList = re.split('.*,.*', args.filterUsers)
    if len(userList) > 0 or args.filterSystemUser:
        byUser = vim.event.EventFilterSpec.ByUsername(userList=userList)
        byUser.systemUser = args.filterSystemUser
        filterSpec.userName = byUser
    eventManager = serviceInstance.content.eventManager
    events = eventManager.QueryEvent(filterSpec)

    for event in events:
        print("%s" % event._wsdlName)
        print("VM: %s" % event.vm.name)
        print("User: %s" % event.userName)
        print("Host: %s -> %s" % (event.sourceHost.name, event.host.name))
        print("Datacenter: %s -> %s" % (event.sourceDatacenter.name,
                                        event.datacenter.name))
        print("Datastore: %s -> %s" % (event.sourceDatastore.name,
                                       event.ds.name))
    print("%s" % events)

if __name__ == '__main__':
    main()
