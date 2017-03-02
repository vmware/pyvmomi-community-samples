#!/usr/bin/env python
# Copyright 2015 Michael Rice <michael@michaelrice.org>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from __future__ import print_function

import atexit

from pyVim import connect

from pyVmomi import vim

from tools import cli
from tools import tasks


def setup_args():

    """Adds additional ARGS to allow the vm name or uuid to
    be set.
    """
    parser = cli.build_arg_parser()
    # using j here because -u is used for user
    parser.add_argument('-j', '--uuid',
                        help='BIOS UUID of the VirtualMachine you want '
                             'to destroy.')
    parser.add_argument('-n', '--name',
                        help='DNS Name of the VirtualMachine you want to '
                             'destroy.')
    parser.add_argument('-i', '--ip',
                        help='IP Address of the VirtualMachine you want to '
                             'destroy')
    parser.add_argument('-v', '--vm',
                        help='VM name of the VirtualMachine you want '
                             'to destroy.')

    my_args = parser.parse_args()

    return cli.prompt_for_password(my_args)


def get_obj(content, vimtype, name):

    """Create contrainer view and search for object in it"""
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if name:
            if c.name == name:
                obj = c
                break
        else:
            obj = c
            break

    container.Destroy()
    return obj

ARGS = setup_args()
SI = None
try:
    SI = connect.SmartConnectNoSSL(host=ARGS.host,
                                   user=ARGS.user,
                                   pwd=ARGS.password,
                                   port=ARGS.port)
    atexit.register(connect.Disconnect, SI)
except (IOError, vim.fault.InvalidLogin):
    pass

if not SI:
    raise SystemExit("Unable to connect to host with supplied credentials.")

VM = None
if ARGS.vm:
    VM = get_obj(SI.content, [vim.VirtualMachine], ARGS.vm)
elif ARGS.uuid:
    VM = SI.content.searchIndex.FindByUuid(None, ARGS.uuid,
                                           True,
                                           False)
elif ARGS.name:
    VM = SI.content.searchIndex.FindByDnsName(None, ARGS.name,
                                              True)
elif ARGS.ip:
    VM = SI.content.searchIndex.FindByIp(None, ARGS.ip, True)

if VM is None:
    raise SystemExit(
        "Unable to locate VirtualMachine. Arguments given: "
        "vm - {0} , uuid - {1} , name - {2} , ip - {3}"
        .format(ARGS.vm, ARGS.uuid, ARGS.name, ARGS.ip)
        )

print("Found: {0}".format(VM.name))
print("The current powerState is: {0}".format(VM.runtime.powerState))
if format(VM.runtime.powerState) == "poweredOn":
    print("Attempting to power off {0}".format(VM.name))
    TASK = VM.PowerOffVM_Task()
    tasks.wait_for_tasks(SI, [TASK])
    print("{0}".format(TASK.info.state))

print("Destroying VM from vSphere.")
TASK = VM.Destroy_Task()
tasks.wait_for_tasks(SI, [TASK])
print("Done.")
