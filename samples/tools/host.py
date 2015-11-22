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
This module implements simple helper functions for python samples working with
virtual machine objects
"""
__author__ = "Timothy C. Quinn (JavaScriptDude)"
from pyVmomi import vim


def print_host_info(host):

    summary = host.summary

    print ".: vim.host.summary :."
    print "- mhost: ", summary.host

    print ".: vim.host.summary.hardware :."
    hardware = summary.hardware
    print " - vendor: ", hardware.vendor
    print " - model: ", hardware.model
    print " - memorySize: ", hardware.memorySize
    print " - cpuModel: ", hardware.cpuModel
    print " - numCpuPkgs: ", hardware.numCpuPkgs
    print " - numCpuCores: ", hardware.numCpuCores
    print " - numCpuThreads: ", hardware.numCpuThreads
    print " - numNics: ", hardware.numNics

    print ".: vim.host.RuntimeInfo :."
    runtime = summary.runtime
    print " - inMaintenanceMode: ", runtime.inMaintenanceMode
    print " - bootTime: ", runtime.bootTime
    print " - powerState: ", runtime.powerState
    print " - standbyMode: ", runtime.standbyMode

    print ".: vim.host.Summary.ConfigSummary :."
    config = summary.config
    print " - name: ", config.name
    print " - sslThumbprint: ", config.sslThumbprint

    print ""
