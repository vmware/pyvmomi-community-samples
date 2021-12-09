# VMware vSphere Python SDK Community Samples Addons
# Copyright (c) 2014-2021 VMware, Inc. All Rights Reserved.
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
This module implements simple helper functions for python samples working with
virtual machine objects
"""
__author__ = "VMware, Inc."


def print_vm_info(vm, depth=1, max_depth=10):
    """
    Print information for a particular virtual machine or recurse into a
    folder with depth protection
    """

    # if this is a group it will have children. if it does, recurse into them
    # and then return
    if hasattr(vm, 'childEntity'):
        if depth > max_depth:
            return
        vm_list = vm.childEntity
        for child_vm in vm_list:
            print_vm_info(child_vm, depth + 1)
        return

    summary = vm.summary
    print("Name       :", summary.config.name)
    print("Path       :", summary.config.vmPathName)
    print("Guest      :", summary.config.guestFullName)
    annotation = summary.config.annotation
    if annotation:
        print("Annotation :", annotation)
    print("State      :", summary.runtime.powerState)
    if summary.guest is not None:
        ip = summary.guest.ipAddress
        if ip:
            print("IP         :", ip)
    if summary.runtime.question is not None:
        print("Question  :", summary.runtime.question.text)
    print("")
