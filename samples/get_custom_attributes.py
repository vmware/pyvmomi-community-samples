#!/usr/bin/env python
# Author: Samuel Krieg
"""
Example listing custom attributes of a VM
"""

from pyVmomi import vim
from tools import cli, service_instance, pchelper


def get_vm(si, content, args):
    """ Return the VM specified in args
    """
    vm = None
    if args.uuid:
        search_index = si.content.searchIndex
        vm = search_index.FindByUuid(None, args.uuid, True)
    elif args.vm_name:
        vm = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)
    return vm


def get_vm_attributes(vm, manager):
    """ Retrieve the VM attributes
    """
    # convert from list to dict for easier lookup
    vm_attributes = {}
    for custom_value in vm.customValue:
        vm_attributes[custom_value.key] = custom_value

    # make a nice dict
    custom_attributes = {}
    for field in manager.field:
        custom_attributes[field.name] = ""
        if field.key in vm_attributes:
            custom_attributes[field.name] = vm_attributes[field.key].value

    return custom_attributes


def main():
    parser = cli.Parser()
    parser.add_optional_arguments(cli.Argument.UUID, cli.Argument.VM_NAME)
    args = parser.get_args()
    si = service_instance.connect(args)
    content = si.RetrieveContent()
    vm = get_vm(si, content, args)

    if not vm:
        raise SystemExit("Unable to locate VirtualMachine.")

    manager = content.customFieldsManager
    custom_attributes = get_vm_attributes(vm, manager)

    # print the result
    for key, value in custom_attributes.items():
        print(f'{key}: {value}')


if __name__ == "__main__":
    main()
