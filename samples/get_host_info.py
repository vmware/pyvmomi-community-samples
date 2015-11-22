#!/usr/bin/env python
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
Python program for listing the host info or information for all hosts managed by vCenter instance
"""

import atexit

from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim

from tools import cli
from tools import host

def main():

    args = cli.get_args()

    try:
        service_instance = connect.SmartConnect(host=args.host,
                                                user=args.user,
                                                pwd=args.password,
                                                port=int(args.port))

        if not service_instance:
            print("Could not connect to the specified host using specified "
                  "username and password")
            return -1

        atexit.register(connect.Disconnect, service_instance)

        content = service_instance.RetrieveContent()
        object_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                              [vim.HostSystem], True)
        for obj in object_view.view:
            host.print_host_info(obj)

        object_view.Destroy()
        return

    except vmodl.MethodFault, e:
        print "Caught vmodl fault : " + e.msg
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
