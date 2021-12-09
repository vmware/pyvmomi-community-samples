# VMware vSphere Python SDK
# Copyright (c) 2008-2021 VMware, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Utility functions for the vSphere API

See com.vmware.apputils.vim25.ServiceUtil in the java API.
"""

from pyVmomi import vim, vmodl


def build_full_traversal():
    """
    Builds a traversal spec that will recurse through all objects .. or at
    least I think it does. additions welcome.

    See com.vmware.apputils.vim25.ServiceUtil.buildFullTraversal in the java
    API. Extended by Sebastian Tello's examples from pysphere to reach networks
    and datastores.
    """

    traversal_spec = vmodl.query.PropertyCollector.TraversalSpec
    selection_spec = vmodl.query.PropertyCollector.SelectionSpec

    # Recurse through all resourcepools
    rp_to_rp = traversal_spec(name='rpToRp', type=vim.ResourcePool, path="resourcePool", skip=False)

    rp_to_rp.selectSet.extend(
        (
            selection_spec(name="rpToRp"),
            selection_spec(name="rpToVm"),
        )
    )

    rp_to_vm = traversal_spec(name='rpToVm', type=vim.ResourcePool, path="vm", skip=False)

    # Traversal through resourcepool branch
    cr_to_rp = traversal_spec(
        name='crToRp', type=vim.ComputeResource, path='resourcePool', skip=False)
    cr_to_rp.selectSet.extend(
        (
            selection_spec(name='rpToRp'),
            selection_spec(name='rpToVm'),
        )
    )

    # Traversal through host branch
    cr_to_h = traversal_spec(name='crToH', type=vim.ComputeResource, path='host', skip=False)

    # Traversal through hostFolder branch
    dc_to_hf = traversal_spec(name='dcToHf', type=vim.Datacenter, path='hostFolder', skip=False)
    dc_to_hf.selectSet.extend(
        (
            selection_spec(name='visitFolders'),
        )
    )

    # Traversal through vmFolder branch
    dc_to_vmf = traversal_spec(name='dcToVmf', type=vim.Datacenter, path='vmFolder', skip=False)
    dc_to_vmf.selectSet.extend(
        (
            selection_spec(name='visitFolders'),
        )
    )

    # Traversal through network folder branch
    dc_to_net = traversal_spec(
        name='dcToNet', type=vim.Datacenter, path='networkFolder', skip=False)
    dc_to_net.selectSet.extend(
        (
            selection_spec(name='visitFolders'),
        )
    )

    # Traversal through datastore branch
    dc_to_ds = traversal_spec(name='dcToDs', type=vim.Datacenter, path='datastore', skip=False)
    dc_to_ds.selectSet.extend(
        (
            selection_spec(name='visitFolders'),
        )
    )

    # Recurse through all hosts
    h_to_vm = traversal_spec(name='hToVm', type=vim.HostSystem, path='vm', skip=False)
    h_to_vm.selectSet.extend(
        (
            selection_spec(name='visitFolders'),
        )
    )

    # Recurse through the folders
    visit_folders = traversal_spec(
        name='visitFolders', type=vim.Folder, path='childEntity', skip=False)
    visit_folders.selectSet.extend(
        (
            selection_spec(name='visitFolders'),
            selection_spec(name='dcToHf'),
            selection_spec(name='dcToVmf'),
            selection_spec(name='dcToNet'),
            selection_spec(name='crToH'),
            selection_spec(name='crToRp'),
            selection_spec(name='dcToDs'),
            selection_spec(name='hToVm'),
            selection_spec(name='rpToVm'),
        )
    )

    full_traversal = selection_spec.Array(
        (visit_folders, dc_to_hf, dc_to_vmf, dc_to_net, cr_to_h, cr_to_rp, dc_to_ds, rp_to_rp,
         h_to_vm, rp_to_vm,))

    return full_traversal


# vim: set ts=4 sw=4 expandtab filetype=python:
