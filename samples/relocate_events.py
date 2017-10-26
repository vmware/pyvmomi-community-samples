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
import sys
from pyVmomi import vim
from pyVim.connect import SmartConnectNoSSL
from pyVim.task import WaitForTask
from tools import cli

__author__ = 'prziborowski'


def setup_args():
    parser = cli.build_arg_parser()
    parser.add_argument('-n', '--name',
                        help='Name of the VM for relocate events')
    parser.add_argument('-d', '--datacenter',
                        help='Name of datacenter to search on. '
                             'Defaults to first.')
    parser.add_argument('--filterUsers',
                        help="Comma-separated list of users to filter on")
    parser.add_argument('--filterSystemUser', action='store_true',
                        help="Filter system user, defaults to false.")
    return cli.prompt_for_password(parser.parse_args())


def main():
    args = setup_args()
    si = SmartConnectNoSSL(host=args.host,
                           user=args.user,
                           pwd=args.password,
                           port=args.port)
    if args.datacenter:
        dc = get_dc(si, args.datacenter)
    else:
        dc = si.content.rootFolder.childEntity[0]

    vm = si.content.searchIndex.FindChild(dc.vmFolder, args.name)
    if vm is None:
        raise Exception('Failed to find VM %s in datacenter %s' %
                        (dc.name, args.name))
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
    eventManager = si.content.eventManager
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
