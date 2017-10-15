#!/usr/bin/env python
# Copyright (c) 2015 Christian Gerbrandt <derchris@derchris.eu>
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
Python port of William Lam's generateHTML5VMConsole.pl
Also ported SHA fingerprint fetching to Python OpenSSL library
"""

import atexit
import OpenSSL
import ssl
import sys
import time

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
from tools import cli


def get_vm(content, name):
    try:
        name = unicode(name, 'utf-8')
    except TypeError:
        pass

    vm = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True)

    for c in container.view:
        if c.name == name:
            vm = c
            break
    return vm


def get_args():
    """
    Add VM name to args
    """
    parser = cli.build_arg_parser()

    parser.add_argument('-n', '--name',
                        required=True,
                        help='Name of Virtual Machine.')
    args = parser.parse_args()
    return cli.prompt_for_password(args)


def main():
    """
    Simple command-line program to generate a URL
    to open HTML5 Console in Web browser
    """

    args = get_args()
    try:
        si = SmartConnect(host=args.host,
                          user=args.user,
                          pwd=args.password,
                          port=int(args.port))
    except Exception as e:
        print('Could not connect to vCenter host')
        print(repr(e))
        sys.exit(1)

    atexit.register(Disconnect, si)

    content = si.RetrieveContent()
    # get virtual machine
    vm = get_vm(content, args.name)
    vm_moid = vm._moId
    # get vCenter server data
    vcenter_data = content.setting
    vcenter_settings = vcenter_data.setting
    vcenter_about = content.about
    vcenter_version = vcenter_about.version

    for item in vcenter_settings:
        key = getattr(item, 'key')
        if key == 'VirtualCenter.FQDN':
            vcenter_fqdn = getattr(item, 'value')

    session_manager = content.sessionManager
    session = session_manager.AcquireCloneTicket()

    vc_cert = ssl.get_server_certificate((args.host, int(args.port)))
    vc_pem = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                             vc_cert)
    vc_fingerprint = vc_pem.digest('sha1')
    # validating version
    if '5' in vcenter_version[:1]:
        console_port = '7331'
        console_path = '/console/'
    elif '6' in vcenter_version[:1]:
        console_port = '9443'
        console_path = '/vsphere-client/webconsole.html'
    else:
        print('vCenter version not supported')
        sys.exit(1)
    # formatting console link
    console_url = "http://{host}:{port}{console_path}?vmId={moid}" \
                  "&vmName={name}&host={vcenter_fqdn}" \
                  "&sessionTicket={session}" \
                  "&thumbprint={vc_fingerprint}".format(
                    host=args.host,
                    port=console_port, console_path=console_path,
                    moid=vm_moid,
                    name=args.name, vcenter_fqdn=vcenter_fqdn,
                    session=session, vc_fingerprint=vc_fingerprint)

    print("Open the following URL in your browser to access the "
          "Remote Console.\n"
          "You have 60 seconds to open the URL, or the session"
          "will be terminated.\n")
    print(console_url)
    print("Waiting for 60 seconds, then exit")
    time.sleep(60)

# Start program
if __name__ == "__main__":
    main()
