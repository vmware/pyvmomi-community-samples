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
Python program for listing the vms on an ESX / vCenter host
"""

import atexit
import ssl

from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim

from tools import cli
from tools import vm


def parse_service_instance(service_instance):
    """
    Print some basic knowledge about your environment as a Hello World
    equivalent for pyVmomi
    """

    content = service_instance.RetrieveContent()
    object_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                          [], True)
    for obj in object_view.view:
        print(obj)
        if isinstance(obj, vim.VirtualMachine):
            vm.print_vm_info(obj)

    object_view.Destroy()
    return


def main():
    """
    Simple command-line program for listing the virtual machines on a system.
    """

    args = cli.get_args()

    try:
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_NONE
        service_instance = connect.SmartConnect(host=args.host,
                                                user=args.user,
                                                pwd=args.password,
                                                port=int(args.port),
                                                sslContext=context)

        if not service_instance:
            print("Could not connect to the specified host using specified "
                  "username and password")
            return -1

        atexit.register(connect.Disconnect, service_instance)

        # ## Do the actual parsing of data ## #
        parse_service_instance(service_instance)

    except vmodl.MethodFault as e:
        print("Caught vmodl fault : {}".format(e.msg))
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
