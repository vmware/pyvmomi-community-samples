#!/usr/bin/env python
"""
Written by Nathan Prziborowski
Github: https://github.com/prziborowski

This code is released under the terms of the Apache 2
http://www.apache.org/licenses/LICENSE-2.0.html

The property collector can be used to fetch a subset of properties
for a large amount of objects with fewer round trips that iterating.

This sample shows how it could be used to fetch the power state of
all the VMs and post-process filter on them.

Note the printing vm.name does cause round-trip per-VM, so it could
be extended in a real script/product to fetch the name property as
well.

I used the ViewManager to gather VMs as it seems easier than making
a traverse spec go through all the datacenters to gather VMs that
may also be in sub-folders.

"""
import sys
from pyVmomi import vim, vmodl
from pyVim.connect import SmartConnectNoSSL, Disconnect
from pyVim.task import WaitForTask
from tools import cli

__author__ = 'prziborowski'


def setup_args():
    parser = cli.build_arg_parser()
    parser.add_argument('-n', '--property', default='runtime.powerState',
                        help='Name of the property to filter by')
    parser.add_argument('-v', '--value', default='poweredOn',
                        help='Value to filter with')
    return cli.prompt_for_password(parser.parse_args())


def get_obj(si, root, vim_type):
    container = si.content.viewManager.CreateContainerView(root, vim_type,
                                                           True)
    view = container.view
    container.Destroy()
    return view


def create_filter_spec(pc, vms, prop):
    objSpecs = []
    for vm in vms:
        objSpec = vmodl.query.PropertyCollector.ObjectSpec(obj=vm)
        objSpecs.append(objSpec)
    filterSpec = vmodl.query.PropertyCollector.FilterSpec()
    filterSpec.objectSet = objSpecs
    propSet = vmodl.query.PropertyCollector.PropertySpec(all=False)
    propSet.type = vim.VirtualMachine
    propSet.pathSet = [prop]
    filterSpec.propSet = [propSet]
    return filterSpec


def filter_results(result, value):
    vms = []
    for o in result.objects:
        if o.propSet[0].val == value:
            vms.append(o.obj)
    return vms


def main():
    args = setup_args()
    si = SmartConnectNoSSL(host=args.host,
                           user=args.user,
                           pwd=args.password,
                           port=args.port)
    # Start with all the VMs from container, which is easier to write than
    # PropertyCollector to retrieve them.
    vms = get_obj(si, si.content.rootFolder, [vim.VirtualMachine])

    pc = si.content.propertyCollector
    filter_spec = create_filter_spec(pc, vms, args.property)
    options = vmodl.query.PropertyCollector.RetrieveOptions()
    result = pc.RetrievePropertiesEx([filter_spec], options)
    vms = filter_results(result, args.value)
    print("VMs with %s = %s" % (args.property, args.value))
    for vm in vms:
        print(vm.name)

    Disconnect(si)


if __name__ == '__main__':
    main()
