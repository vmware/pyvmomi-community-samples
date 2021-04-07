#!/usr/bin/env python
"""
Written by Reuben ur Rahman
Github: https://github.com/rreubenur
Email: reuben.13@gmail.com

Linked clone example
"""

import requests.packages.urllib3 as urllib3
from pyVmomi import vim
from tools import cli, tasks, pchelper, service_instance


def _clone_vm(si, template, vm_name, vm_folder, location):
    clone_spec = vim.vm.CloneSpec(
        powerOn=True, template=False, location=location,
        snapshot=template.snapshot.rootSnapshotList[0].snapshot)
    task = template.Clone(name=vm_name, folder=vm_folder, spec=clone_spec)
    tasks.wait_for_tasks(si, [task])
    print("Successfully cloned and created the VM '{}'".format(vm_name))


def _get_relocation_spec(host, resource_pool):
    relospec = vim.vm.RelocateSpec()
    relospec.diskMoveType = 'createNewChildDiskBacking'
    relospec.host = host
    relospec.pool = resource_pool
    return relospec


def _take_template_snapshot(si, vm):
    if len(vm.rootSnapshot) < 1:
        task = vm.CreateSnapshot_Task(name='test_snapshot',
                                      memory=False,
                                      quiesce=False)
        tasks.wait_for_tasks(si, [task])
        print("Successfully taken snapshot of '{}'".format(vm.name))


def main():
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.VM_NAME, cli.Argument.TEMPLATE)
    parser.add_optional_arguments(cli.Argument.DATACENTER_NAME, cli.Argument.CLUSTER_NAME, cli.Argument.ESX_NAME)
    args = parser.get_args()

    urllib3.disable_warnings()
    print("Connected to vCenter Server")
    si = service_instance.connect(args)

    content = si.RetrieveContent()

    datacenter = pchelper.search_for_obj(content, [vim.Datacenter], args.datacenter_name)
    if not datacenter:
        raise Exception("Couldn't find the Datacenter with the provided name "
                        "'{}'".format(args.datacenter_name))

    cluster = pchelper.search_for_obj(content, [vim.ClusterComputeResource], args.cluster_name, datacenter.hostFolder)

    if not cluster:
        raise Exception("Couldn't find the Cluster with the provided name "
                        "'{}'".format(args.cluster_name))

    host_obj = None
    for host in cluster.host:
        if host.name == args.esx_name:
            host_obj = host
            break

    vm_folder = datacenter.vmFolder

    template = pchelper.search_for_obj(content, [vim.VirtualMachine], args.template, vm_folder)

    if not template:
        raise Exception("Couldn't find the template with the provided name "
                        "'{}'".format(args.template))

    location = _get_relocation_spec(host_obj, cluster.resourcePool)
    _take_template_snapshot(si, template)
    _clone_vm(si, template, args.vm_name, vm_folder, location)


if __name__ == "__main__":
    main()
