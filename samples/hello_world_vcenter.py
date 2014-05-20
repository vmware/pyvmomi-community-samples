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
Python program to authenticate and print
a friendly encouragement to joining the community!
"""

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vmodl

import pyvmomi_addons.cli as cli

import atexit


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
            print "Could not connect to specified host using specified "
            + "username & password"
            return -1

        atexit.register(Disconnect, ServiceInstance)

        print "\nHello World!\n"
        print "If you got here, you authenticted into vCenter."
        print "The server is " + args.host + "!"
        print "Well done!"
        print "\n"
        print "Download, learn and contribute back:"
        print "https://github.com/vmware/pyvmomi-community-samples"
        print "\n\n"

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
