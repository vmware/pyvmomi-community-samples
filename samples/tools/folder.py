# VMware vSphere Python SDK Community Samples Addons
# Copyright (c) 2014 VMware, Inc. All Rights Reserved.
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
This module implements simple finder functions for ServiceInstance
"""
__author__ = "VMware, Inc."


from pyVmomi import vim


def search_for_entity_by_name(folder, name):
    """Search for an entity by name.

    Given any subtype of vim.ManagedEntity such as vim.Datastore or
    vim.VirtualMachine this method will search within the folder
    for an instance of the type with the name supplied.

    @type folder: vim.Folder
    @param folder: The top most folder to recursively search for the child.

    @type name: String
    @param name: Name of the child you are looking for, assumed to be unique.

    @rtype: vim.ManagedEntity
    @return: the found entity or None if no entity found.
    """
    entity_stack = folder.childEntity

    while entity_stack:
        entity = entity_stack.pop()
        if entity.name == name:
            return entity
        elif isinstance(entity, vim.Datacenter):
            # add this vim.DataCenter's folders to our search
            entity_stack.append(entity.datastoreFolder)
            entity_stack.append(entity.hostFolder)
            entity_stack.append(entity.networkFolder)
            entity_stack.append(entity.vmFolder)
        elif isinstance(entity, vim.Folder):
            # add all child entities from this folder to our search
            entity_stack.extend(entity.childEntity)


def init():
    vim.Folder.find_child_by_name = search_for_entity_by_name
