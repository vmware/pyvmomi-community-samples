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
from __future__ import print_function

import atexit

import requests

from pyVim import connect
from pyVmomi import vim
from tools import cli
from tools import tasks

requests.packages.urllib3.disable_warnings()


def setup_args():
    """
    Adds additional args to allow the vm uuid to
    be set.
    """
    parser = cli.build_arg_parser()
    # using j here because -u is used for user
    parser.add_argument('-j', '--uuid',
                        required=True,
                        help='UUID of the VirtualMachine you want to add '
                             'metadata to.')
    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)

args = setup_args()
si = None
try:
    si = connect.SmartConnect(host=args.host,
                              user=args.user,
                              pwd=args.password,
                              port=int(args.port))
    atexit.register(connect.Disconnect, si)
except IOError:
    pass

if not si:
    raise SystemExit("Unable to connect to host with supplied info.")
vm = si.content.searchIndex.FindByUuid(None, args.uuid, True)
if not vm:
    raise SystemExit("Unable to locate VirtualMachine.")

print("Found: {0}".format(vm.name))

spec = vim.vm.ConfigSpec()
opt = vim.option.OptionValue()
spec.extraConfig = []

options_values = {
    "custom_key1": "Ive tested very large xml and json, and base64 values here"
                   " and they work",
    "custom_key2": "Ive tested very large xml and json, and base64 values here"
                   " and they work",
    "custom_key3": "Ive tested very large xml and json, and base64 values here"
                   " and they work",
    "custom_key4": "Ive tested very large xml and json, and base64 values here"
                   " and they work"
}

for k, v in options_values.iteritems():
    opt.key = k
    opt.value = v
    spec.extraConfig.append(opt)
    opt = vim.option.OptionValue()

task = vm.ReconfigVM_Task(spec)
tasks.wait_for_tasks(si, [task])
print("Done setting values.")
print("time to get them")
keys_and_vals = vm.config.extraConfig
for opts in keys_and_vals:
    print("key: {0} => {1}".format(opts.key, opts.value))
print("done.")
