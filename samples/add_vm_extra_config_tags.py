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

from pyVmomi import vim
from tools import cli, service_instance,pchelper, tasks

requests.packages.urllib3.disable_warnings()

parser = cli.Parser()
parser.add_optional_arguments(cli.Argument.UUID, cli.Argument.VM_NAME)
args = parser.get_args()
serviceInstance = service_instance.connect(args)

vm = None
if args.uuid:
    vm = serviceInstance.content.searchIndex.FindByUuid(None, args.uuid, True)
elif args.vm_name:
    vm = pchelper.get_obj(serviceInstance.RetrieveContent(), [vim.VirtualMachine], args.vm_name)
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

for k, v in options_values.items():
    opt.key = k
    opt.value = v
    spec.extraConfig.append(opt)
    opt = vim.option.OptionValue()

task = vm.ReconfigVM_Task(spec)
tasks.wait_for_tasks(serviceInstance, [task])
print("Done setting values.")
print("time to get them")
keys_and_vals = vm.config.extraConfig
for opts in keys_and_vals:
    print("key: {0} => {1}".format(opts.key, opts.value))
print("done.")
