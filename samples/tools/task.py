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
This module implements simple helper functions for pyvmomi
"""
__author__ = "VMware, Inc."

from pyVim import connect
from pyVmomi import vim
from pyVmomi import vmodl


def _wait_for_task_helper(self, timeout=0, callback=None):
    """A helper to inject into the task class.

    This dynamic helper allows you to call wait() on any task to keep the
    python process from advancing until the

    """
    si = connect.GetSi()
    pc = si.content.propertyCollector
    objSpecs = [vmodl.query.PropertyCollector.ObjectSpec(obj=self)]
    propSpec = vmodl.query.PropertyCollector.PropertySpec(type=vim.Task,
                                                          pathSet=[], all=True)
    filterSpec = vmodl.query.PropertyCollector.FilterSpec()
    filterSpec.objectSet = objSpecs
    filterSpec.propSet = [propSpec]
    filter = pc.CreateFilter(filterSpec, True)
    try:
        options = vim.WaitOptions()
        options.maxWaitSeconds = timeout
        while True:
            if callback:
                callback()
            update = pc.WaitForUpdatesEx(None, options)
            for filterSet in update.filterSet:
                for objSet in filterSet.objectSet:
                    task = objSet.obj
                    for change in objSet.changeSet:
                        if change.name == 'info':
                            state = change.val.state
                        elif change.name == 'info.state':
                            state = change.val
                        else:
                            continue

                        if state == vim.TaskInfo.State.success:
                            return True
                        elif state == vim.TaskInfo.State.error:
                            raise task.info.error
    finally:
        if filter:
            filter.Destroy()


def init():
    """Initializes task helper methods.

    This package injects helper methods into vim.Task and related objects.
    The helpers will not be available until this method is invoked. This
    allows for alternative monkey-patching systems to live within the same
    library suite.
    """
    vim.Task.wait = _wait_for_task_helper
