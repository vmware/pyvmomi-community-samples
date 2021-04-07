#!/usr/bin/env python
# VMware vSphere Python SDK
# Copyright (c) 2008-2021 VMware, Inc. All Rights Reserved.
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
A Python script for changing the name of an object. Demonstrates the use
of tasks in an asynchronous way.
"""

import sys
import time
from pyVmomi import vim
from tools import cli, service_instance


parser = cli.Parser()
parser.add_required_arguments(cli.Argument.NAME)
parser.add_optional_arguments(cli.Argument.NEW_NAME)
args = parser.get_args()

# form a connection...
serviceInstance = service_instance.connect(args)

# search the whole inventory tree recursively... a brutish but effective tactic
root_folder = serviceInstance.content.rootFolder
entity_stack = root_folder.childEntity
name = args.name
obj = None
while entity_stack:
    entity = entity_stack.pop()
    if entity.name == name:
        obj = entity
        break
    elif isinstance(entity, vim.Datacenter):
        # add this vim.DataCenter's folders to our search
        # we don't know the entity's type so we have to scan
        # each potential folder...
        entity_stack.append(entity.datastoreFolder)
        entity_stack.append(entity.hostFolder)
        entity_stack.append(entity.networkFolder)
        entity_stack.append(entity.vmFolder)
    elif isinstance(entity, vim.Folder):
        # add all child entities from this folder to our search
        entity_stack.extend(entity.childEntity)

if obj is None:
    print("A object named %s could not be found" % args.name)
    exit()

if args.new_name:
    new_name = args.new_name
else:
    # just because we want the script to do *something*
    new_name = args.name + "0"

print("\n")
print("name        : %s" % obj.name)
print("\n")
print("    renaming from %s to %s" % (args.name, new_name))
print("\n")

# rename creates a task...
task = obj.Rename(new_name)

# Did you know that task objects in pyVmomi get updates automatically?
# Check this out... it's not super efficient but here's how you could
# have a script that looped waiting on a task but still had the
# chance to periodically check other things or do other actions...
print("rename task state:")
count = 0
state = task.info.state
while task.info.state != vim.TaskInfo.State.success:
    sys.stdout.write("\r\t" + str(time.time()) + "\t: " + task.info.state)
    sys.stdout.flush()
    count += 1

print("\nrename finished\n")
