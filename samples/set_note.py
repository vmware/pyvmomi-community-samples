#!/usr/bin/env python
# Copyright 2014 Michael Rice
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import atexit

from pyVim import connect
from pyVmomi import vim
from tools import cli
from tools import tasks


def setup_args():
    """
    Adds additional args to allow the vm uuid to
    be set.
    """
    parser = cli.build_arg_parser()
    # using j here because -u is used for user
    parser.add_argument('-j', '--uuid',
                        required=True,
                        help='UUID of the VirtualMachine you want to add a '
                             'note to.')
    parser.add_argument('-m', '--message',
                        required=True,
                        help="Message to add to the notes field.")
    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)

args = setup_args()
si = None
try:
    si = connect.SmartConnectNoSSL(host=args.host,
                                   user=args.user,
                                   pwd=args.password,
                                   port=int(args.port))
    atexit.register(connect.Disconnect, si)
except IOError as e:
    print(e)
    pass

if not si:
    raise SystemExit("Unable to connect to host with supplied info.")
vm = si.content.searchIndex.FindByUuid(None, args.uuid, True)
if not vm:
    raise SystemExit("Unable to locate VirtualMachine.")

print("Found: {0}".format(vm.name))
spec = vim.vm.ConfigSpec()
spec.annotation = args.message
task = vm.ReconfigVM_Task(spec)
tasks.wait_for_tasks(si, [task])
print("Done.")
