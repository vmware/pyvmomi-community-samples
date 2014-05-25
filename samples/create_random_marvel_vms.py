#!/usr/bin/env python
# William lam
# www.virtuallyghetto.com

"""
vSphere SDK for Python program for creating tiny VMs (1vCPU/128MB) with random
names using the Marvel Commics API
"""

import argparse
import atexit
import getpass
import hashlib
import json
import random
import requests
import time

from pyVim import connect
from pyVmomi import vim
from pyVmomi import vmodl

from tools import cli


def get_args():
    """
    Use the tools.cli methods and then add a few more arguments.
    """
    parser = cli.build_arg_parser()

    parser.add_argument('-c', '--count',
                        type=int,
                        required=True,
                        action='store',
                        help='Number of VMs to create')

    parser.add_argument('-d', '--datastore',
                        required=True,
                        action='store',
                        help='Name of Datastore to create VM in')

    # NOTE (hartsock): as a matter of good security practice, never ever
    # save a credential of any kind in the source code of a file. As a
    # matter of policy we want to show people good programming practice in
    # these samples so that we don't encourage security audit problems for
    # people in the future.

    parser.add_argument('-k', '--public_key_file',
                        required=False,
                        action='store',
                        help='Name of the file holding your marvel public key,'
                             ' the key should be the first only of the file. '
                             'Set one up at developer.marvel.com/account')

    parser.add_argument('-e', '--private_key_file',
                        required=False,
                        action='store',
                        help='Name of the file holding your marvel private '
                             'key, the key should be the only line of the '
                             'file. '
                             'Set one up at developer.marvel.com/account')

    args = parser.parse_args()

    return cli.prompt_for_password(args)


def get_marvel_characters(number_of_characters,
                          marvel_public_key,
                          marvel_private_key):
    timestamp = str(int(time.time()))
    # hash is required as part of request which is
    # md5(timestamp + private + public key)
    hash_value = hashlib.md5(timestamp + marvel_private_key +
                             marvel_public_key).hexdigest()

    characters = []
    for x in xrange(number_of_characters):
        # randomly select one of the 1402 Marvel character
        offset = random.randrange(1, 1402)
        limit = '1'

        # GET /v1/public/characters
        url = ('http://gateway.marvel.com:80/v1/public/characters?limit=' +
               limit + '&offset=' + str(offset) + '&apikey=' +
               marvel_public_key + '&ts=' + timestamp + '&hash=' + hash_value)

        headers = {'content-type': 'application/json'}
        request = requests.get(url, headers=headers)
        data = json.loads(request.content)
        if data.get('code') == 'InvalidCredentials':
            raise RuntimeError('Your Marvel API keys do not work!')

        # retrieve character name & replace spaces with underscore so we don't
        # have stupid spaces in our VM names
        character = data['data']['results'][0]['name'].strip().replace(' ',
                                                                       '_')
        characters.append(character)
    return characters


def CreateDummyVM(name, si, vmFolder, rp, datastore):
    vmName = 'MARVEL-' + name
    datastorePath = '[' + datastore + '] ' + vmName

    # bare minimum VM shell, no disks. Feel free to edit
    file = vim.vm.FileInfo(logDirectory=None, snapshotDirectory=None,
                           suspendDirectory=None, vmPathName=datastorePath)

    config = vim.vm.ConfigSpec(name=vmName, memoryMB=128, numCPUs=1,
                               files=file, guestId='dosGuest',
                               version='vmx-07')

    print "Creating VM " + vmName + " ..."
    task = vmFolder.CreateVM_Task(config=config, pool=rp)
    WaitForTasks([task], si)


# borrowed from poweronvm.py sample
def WaitForTasks(tasks, si):
    """
    Given the service instance si and tasks, it returns after all the
    tasks are complete
    """

    pc = si.content.propertyCollector

    taskList = [str(task) for task in tasks]

    # Create filter
    objSpecs = [vmodl.query.PropertyCollector.ObjectSpec(obj=task)
                for task in tasks]
    propSpec = vmodl.query.PropertyCollector.PropertySpec(type=vim.Task,
                                                          pathSet=[], all=True)
    filterSpec = vmodl.query.PropertyCollector.FilterSpec()
    filterSpec.objectSet = objSpecs
    filterSpec.propSet = [propSpec]
    filter = pc.CreateFilter(filterSpec, True)

    try:
        version, state = None, None

        # Loop looking for updates till the state moves to a completed state.
        while len(taskList):
            update = pc.WaitForUpdates(version)
            for filterSet in update.filterSet:
                for objSet in filterSet.objectSet:
                    task = objSet.obj
                    for change in objSet.changeSet:
                        if change.name == 'info':
                            state = change.val.state
                        elif change.name == 'info.state':
                            state = change.val
                        else:
                            continue

                        if not str(task) in taskList:
                            continue

                        if state == vim.TaskInfo.State.success:
                            # Remove task from taskList
                            taskList.remove(str(task))
                        elif state == vim.TaskInfo.State.error:
                            raise task.info.error
            # Move to next version
            version = update.version
    finally:
        if filter:
            filter.Destroy()


def main():
    """
    Simple command-line program for creating Dummy VM based on Marvel character
    names
    """

    args = get_args()

    if args.public_key_file:
        with open(args.public_key_file) as key_file:
            marvel_public_key = key_file.readline().strip()
    else:
        marvel_public_key = raw_input('Marvel public key: ').strip()

    if args.private_key_file:
        with open(args.private_key_file) as key_file:
            marvel_private_key = key_file.readline().strip()
    else:
        marvel_private_key = raw_input('Marvel private key: ').strip()

    try:
        si = None
        try:
            si = connect.SmartConnect(host=args.host,
                                      user=args.user,
                                      pwd=args.password,
                                      port=int(args.port))
        except IOError, e:
            pass
        if not si:
            print("Could not connect to the specified host using specified "
                  "username and password")
            return -1

        atexit.register(connect.Disconnect, si)

        content = si.RetrieveContent()
        datacenter = content.rootFolder.childEntity[0]
        vmFolder = datacenter.vmFolder
        hosts = datacenter.hostFolder.childEntity
        rp = hosts[0].resourcePool

        print("Connecting to Marvel API and retrieving " + str(args.count) +
              " random character(s) ...")

        characters = get_marvel_characters(args.count,
                                           marvel_public_key,
                                           marvel_private_key)

        for name in characters:
            CreateDummyVM(name, si, vmFolder, rp, args.datastore)

    except vmodl.MethodFault, e:
        print "Caught vmodl fault : " + e.msg
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
