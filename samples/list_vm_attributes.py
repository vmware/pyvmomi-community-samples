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
from __future__ import print_function
import atexit

from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim
import ssl
import atexit
import argparse
import getpass
import tools.cli as cli

def get_args():
    parser = argparse.ArgumentParser(
        description='Arguments for talking to vCenter')

    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='vSpehre service to connect to')

    parser.add_argument('-o', '--port',
                        type=int,
                        default=443,
                        action='store',
                        help='Port to connect on')

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='User name to use')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to use')

    parser.add_argument('--no-ssl-verify',
                        required=False,
                        action='store',
                        help='use self signed SSL certificates')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password')

    return args


def print_vm_info(virtual_machine, f):
    """
    Print information for a particular virtual machine or recurse into a
    folder with depth protection
    """
    summary = virtual_machine.summary
    print("Name          : %s" % summary.config.name)
    print("Template      : %s" % summary.config.template)
    print("Path          : %s" % summary.config.vmPathName)
    print("Guest         : %s" % summary.config.guestFullName)
    print("Instance UUID : %s" % summary.config.instanceUuid)
    print("Bios UUID     : %s" % summary.config.uuid)
    annotation = summary.config.annotation
    if annotation:
        print("Annotation   : %s" % annotation)
    print("State         : %s" % summary.runtime.powerState)
    if summary.guest is not None:
        ip_address = summary.guest.ipAddress
        tools_version = summary.guest.toolsStatus
        if tools_version is not None:
            print("VMware-tools  : %s" % tools_version)
        else:
            print("Vmware-tools  : None")
        if ip_address:
            print("IP            : %s" % ip_address)
        else:
            print("IP            : None")
        print("Attributes    :")
        for k, v in [(x.name, v.value) for x in f for v in virtual_machine.customValue if x.key == v.key]:
            print("          Name: %s\n         Value: %s" % (k, v))

    if summary.runtime.question is not None:
        print("Question    : %s" % summary.runtime.question.text)
    print("")


def main():
    """
    Simple command-line program for listing the virtual machines on a system
    including custom attributes.
    """

    args = get_args()

    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    if args.no_ssl_verify:
        context.verify_mode = ssl.CERT_NONE

    try:
        service_instance = connect.SmartConnect(host=args.host,
                                                user=args.user,
                                                pwd=args.password,
                                                port=int(args.port),
                                                sslContext=context)

        atexit.register(connect.Disconnect, service_instance)

        content = service_instance.RetrieveContent()

        container = content.rootFolder  # starting point to look into
        viewType = [vim.VirtualMachine]  # object types to look for
        recursive = True  # whether we should look into it recursively
        containerView = content.viewManager.CreateContainerView(
            container, viewType, recursive)

        f = service_instance.content.customFieldsManager.field

        children = containerView.view
        for child in children:
            print_vm_info(child, f)

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
