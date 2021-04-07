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

from pyVmomi import vim
from tools import cli, service_instance, tasks, pchelper


parser = cli.Parser()
parser.add_required_arguments(cli.Argument.MESSAGE)
parser.add_optional_arguments(cli.Argument.UUID, cli.Argument.VM_NAME)
args = parser.get_args()
serviceInstance = service_instance.connect(args)

vm = None
if args.uuid:
    search_index = serviceInstance.content.searchIndex
    vm = search_index.FindByUuid(None, args.uuid, True)
elif args.vm_name:
    content = serviceInstance.RetrieveContent()
    vm = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)

if not vm:
    raise SystemExit("Unable to locate VirtualMachine.")

print("Found: {0}".format(vm.name))
spec = vim.vm.ConfigSpec()
spec.annotation = args.message
task = vm.ReconfigVM_Task(spec)
tasks.wait_for_tasks(serviceInstance, [task])
print("Done.")
