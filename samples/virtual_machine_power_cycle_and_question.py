#!/usr/bin/env python
# Copyright (c) 2014 VMware, Inc. All Rights Reserved.
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
A Python script for power cycling a virtual machine. Demonstrates the use
of tasks in an asynchronous way. And how to answer virtual machine
questions in the middle of power operations.
"""

import atexit
import argparse
import getpass
import sys
import textwrap
import time

from pyVim import connect
from pyVmomi import vim


def get_args():
    parser = argparse.ArgumentParser()

    # because -h is reserved for 'help' we use -s for service
    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='vSphere service to connect to')

    # because we want -p for password, we use -o for port
    parser.add_argument('-o', '--port',
                        type=int,
                        default=443,
                        action='store',
                        help='Port to connect on')

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='User name to use when connecting to host')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to use when connecting to host')
    parser.add_argument('-n', '--name',
                        required=True,
                        action='store',
                        help='Name of the virtual_machine to look for.')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password for host %s and user %s: ' %
                   (args.host, args.user))

    return args


def _create_char_spinner():
    """Creates a generator yielding a char based spinner.
    """
    while True:
        for c in '|/-\\':
            yield c


_spinner = _create_char_spinner()


def spinner(label=''):
    """Prints label with a spinner.

    When called repeatedly from inside a loop this prints
    a one line CLI spinner.
    """
    sys.stdout.write("\r\t%s %s" % (label, _spinner.next()))
    sys.stdout.flush()


def answer_vm_question(virtual_machine):
    print "\n"
    choices = virtual_machine.runtime.question.choice.choiceInfo
    default_option = None
    if virtual_machine.runtime.question.choice.defaultIndex is not None:
        ii = virtual_machine.runtime.question.choice.defaultIndex
        default_option = choices[ii]
    choice = None
    while choice not in [o.key for o in choices]:
        print "VM power on is paused by this question:\n\n"
        print "\n".join(textwrap.wrap(
            virtual_machine.runtime.question.text, 60))
        for option in choices:
            print "\t %s: %s " % (option.key, option.label)
        if default_option is not None:
            print "default (%s): %s\n" % (default_option.label,
                                          default_option.key)
        choice = raw_input("\nchoice number: ").strip()
        print "..."
    return choice


# form a connection...
args = get_args()
si = connect.SmartConnect(host=args.host, user=args.user, pwd=args.password,
                          port=args.port)

# doing this means you don't need to remember to disconnect your script/objects
atexit.register(connect.Disconnect, si)

# search the whole inventory tree recursively... a brutish but effective tactic
vm = None
entity_stack = si.content.rootFolder.childEntity
while entity_stack:
    entity = entity_stack.pop()

    if entity.name == args.name:
        vm = entity
        del entity_stack[0:len(entity_stack)]
    elif hasattr(entity, 'childEntity'):
        entity_stack.extend(entity.childEntity)
    elif isinstance(entity, vim.Datacenter):
        entity_stack.append(entity.vmFolder)

if not isinstance(vm, vim.VirtualMachine):
    print "could not find a virtual machine with the name %s" % args.name
    sys.exit(-1)

print "Found VirtualMachine: %s Name: %s" % (vm, vm.name)

if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
    # using time.sleep we just wait until the power off action
    # is complete. Nothing fancy here.
    print "powering off..."
    task = vm.PowerOff()
    while task.info.state not in [vim.TaskInfo.State.success,
                                  vim.TaskInfo.State.error]:
        time.sleep(1)
    print "power is off."


# Sometimes we don't want a task to block execution completely
# we may want to execute or handle concurrent events. In that case we can
# poll our task repeatedly and also check for any run-time issues. This
# code deals with a common problem, what to do if a VM question pops up
# and how do you handle it in the API?
print "powering on VM %s" % vm.name
if vm.runtime.powerState != vim.VirtualMachinePowerState.poweredOn:

    # now we get to work... calling the vSphere API generates a task...
    task = vm.PowerOn()

    # We track the question ID & answer so we don't end up answering the same
    # questions repeatedly.
    answers = {}
    while task.info.state not in [vim.TaskInfo.State.success,
                                  vim.TaskInfo.State.error]:

        # we'll check for a question, if we find one, handle it,
        # Note: question is an optional attribute and this is how pyVmomi
        # handles optional attributes. They are marked as None.
        if vm.runtime.question is not None:
            question_id = vm.runtime.question.id
            if question_id not in answers.keys():
                answers[question_id] = answer_vm_question(vm)
                vm.AnswerVM(question_id, answers[question_id])

        # create a spinning cursor so people don't kill the script...
        spinner(task.info.state)

    if task.info.state == vim.TaskInfo.State.error:
        # some vSphere errors only come with their class and no other message
        print "error type: %s" % task.info.error.__class__.__name__
        print "found cause: %s" % task.info.error.faultCause
        for fault_msg in task.info.error.faultMessage:
            print fault_msg.key
            print fault_msg.message
        sys.exit(-1)

print
sys.exit(0)
