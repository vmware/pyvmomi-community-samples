#!/usr/bin/python
# VMware vSphere Python SDK
# Copyright (c) 2008-2013 VMware, Inc. All Rights Reserved.
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
Python program for listing the vms on an ESX / vCenter host
"""

from optparse import OptionParser, make_option
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vmodl

import pyvmomi_addons.cli as cli

import atexit


def PrintVmInfo(vm, depth=1):
    """
    Print information for a particular virtual machine or recurse into a
    folder with depth protection
    """
    maxdepth = 10

    # if this is a group it will have children. if it does, recurse into them
    #  and then return
    if hasattr(vm, 'childEntity'):
        if depth > maxdepth:
            return
        vmList = vm.childEntity
        for c in vmList:
            PrintVmInfo(c, depth + 1)
        return

    summary = vm.summary
    print "Name       : ", summary.config.name
    print "Path       : ", summary.config.vmPathName
    print "Guest      : ", summary.config.guestFullName
    annotation = summary.config.annotation
    if annotation:
        print "Annotation : ", annotation
    print "State      : ", summary.runtime.powerState
    if summary.guest:
        ip = summary.guest.ipAddress
        if ip:
            print "IP         : ", ip
    if summary.runtime.question is not None:
        print "Question  : ", summary.runtime.question.text
    print ""


def ParseServiceInstance(ServiceInstance):
    """
    Print some basic knowledge about your environment as a Hello World
    equivalent for pyVmomi
    """

    content = ServiceInstance.RetrieveContent()
    objView = content.viewManager.CreateContainerView(content.rootFolder, [],
                                                      True)
    for obj in objView.view:
        print obj

    objView.Destroy()
    # for vm in vmList:
    #    if (vm.name in vmnames) and (vm.runtime.powerState == "poweredOn"):
    #        vmObj = vm
    #        PrintVmInfo(vmObj,content,args.int)
    return


def main():
    """
    Simple command-line program for listing the virtual machines on a system.
    """

    args = cli.get_args()

    try:
        ServiceInstance = None
        try:
            ServiceInstance = SmartConnect(host=args.host,
                                           user=args.user,
                                           pwd=args.password,
                                           port=int(args.port))
        except IOError, e:
            pass
        if not ServiceInstance:
            print("Could not connect to the specified host using specified "
                  "username and password")
            return -1

        atexit.register(Disconnect, ServiceInstance)

        # ## Do the actual parsing of data ## #
        ParseServiceInstance(ServiceInstance)

    except vmodl.MethodFault, e:
        print "Caught vmodl fault : " + e.msg
        return -1
    except Exception, e:
        print "Caught exception : " + str(e)
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
