#!/usr/bin/env python
"""
Written by Reuben ur Rahman
Github: https://github.com/rreubenur
Email: reuben.13@gmail.com

Linked clone example
"""

import atexit
import requests.packages.urllib3 as urllib3
import ssl

from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect

from tools import cli
from tools import tasks


def get_args():
    parser = cli.build_arg_parser()
    parser.add_argument('-v', '--vm_name',
                        required=True,
                        action='store',
                        help='Name of the new VM')

    parser.add_argument('--template_name',
                        required=True,
                        action='store',
                        help='Name of the template/VM you are cloning from')

    parser.add_argument('--datacenter_name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the Datacenter you wish to use.')

    parser.add_argument('--cluster_name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the cluster you wish to use')

    parser.add_argument('--host_name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the cluster you wish to use')

    args = parser.parse_args()

    cli.prompt_for_password(args)
    return args


def get_obj(content, vimtype, name, folder=None):
    obj = None
    if not folder:
        folder = content.rootFolder
    container = content.viewManager.CreateContainerView(folder, vimtype, True)
    for item in container.view:
        if item.name == name:
            obj = item
            break
    return obj


def _clone_vm(si, template, vm_name, vm_folder, location):
    clone_spec = vim.vm.CloneSpec(
        powerOn=True, template=False, location=location,
        snapshot=template.snapshot.rootSnapshotList[0].snapshot)
    task = template.Clone(name=vm_name, folder=vm_folder, spec=clone_spec)
    tasks.wait_for_tasks(si, [task])
    print "Successfully cloned and created the VM '{}'".format(vm_name)


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
        print "Successfully taken snapshot of '{}'".format(vm.name)


def main():
    args = get_args()

    urllib3.disable_warnings()
    si = None
    context = None
    if hasattr(ssl, 'SSLContext'):
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_NONE
    if context:
        # Python >= 2.7.9
        si = SmartConnect(host=args.host,
                          port=int(args.port),
                          user=args.user,
                          pwd=args.password,
                          sslContext=context)
    else:
        # Python >= 2.7.7
        si = SmartConnect(host=args.host,
                          port=int(args.port),
                          user=args.user,
                          pwd=args.password)
    atexit.register(Disconnect, si)
    print "Connected to vCenter Server"

    content = si.RetrieveContent()

    datacenter = get_obj(content, [vim.Datacenter], args.datacenter_name)
    if not datacenter:
        raise Exception("Couldn't find the Datacenter with the provided name "
                        "'{}'".format(args.datacenter_name))

    cluster = get_obj(content, [vim.ClusterComputeResource], args.cluster_name,
                      datacenter.hostFolder)

    if not cluster:
        raise Exception("Couldn't find the Cluster with the provided name "
                        "'{}'".format(args.cluster_name))

    host_obj = None
    for host in cluster.host:
        if host.name == args.host_name:
            host_obj = host
            break

    vm_folder = datacenter.vmFolder

    template = get_obj(content, [vim.VirtualMachine], args.template_name,
                       vm_folder)

    if not template:
        raise Exception("Couldn't find the template with the provided name "
                        "'{}'".format(args.template_name))

    location = _get_relocation_spec(host_obj, cluster.resourcePool)
    _take_template_snapshot(si, template)
    _clone_vm(si, template, args.vm_name, vm_folder, location)

if __name__ == "__main__":
    main()
