#!/usr/bin/env python
# William lam
# www.virtuallyghetto.com

"""
vSphere SDK for Python program for creating tiny VMs (1vCPU/128MB) with random
names using the Marvel Comics API
"""

import atexit
import hashlib
import json

import random
import time

import requests
from pyVim import connect
from pyVmomi import vim

from tools import cli
from tools import tasks

from add_nic_to_vm import add_nic, get_obj

try:
    input = raw_input
except NameError:
    pass


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

    parser.add_argument('--datacenter',
                        required=True,
                        help='Name of the datacenter to create VM in.')

    parser.add_argument('--folder',
                        required=True,
                        help='Name of the vm folder to create VM in.')

    parser.add_argument('--resource-pool',
                        required=True,
                        help='Name of resource pool to create VM in.')

    parser.add_argument('--opaque-network',
                        help='Name of the opaque network to add to the new VM')

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


def get_marvel_characters(number_of_characters, marvel_public_key,
                          marvel_private_key):
    """Makes an API call to the Marvel Comics developer API
        to get a list of character names.

    :param number_of_characters: int Number of characters to fetch.
    :param marvel_public_key: String Public API key from Marvel
    :param marvel_private_key: String Private API key from Marvel
    :rtype list: Containing names of characters
    """
    timestamp = str(int(time.time()))
    # hash is required as part of request which is
    # md5(timestamp + private + public key)
    hash_value = hashlib.md5((timestamp + marvel_private_key +
                              marvel_public_key).encode('utf-8')).hexdigest()

    characters = []
    for _num in range(number_of_characters):
        # randomly select one of the 1478 Marvel characters
        offset = random.randrange(1, 1478)
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
        # have spaces in our VM names
        character = data['data']['results'][0]['name'].strip().replace(' ',
                                                                       '_')
        characters.append(character)
    return characters


def create_dummy_vm(vm_name, service_instance, vm_folder, resource_pool,
                    datastore):
    """Creates a dummy VirtualMachine with 1 vCpu, 128MB of RAM.

    :param name: String Name for the VirtualMachine
    :param service_instance: ServiceInstance connection
    :param vm_folder: Folder to place the VirtualMachine in
    :param resource_pool: ResourcePool to place the VirtualMachine in
    :param datastore: DataStrore to place the VirtualMachine on
    """
    datastore_path = '[' + datastore + '] ' + vm_name

    # bare minimum VM shell, no disks. Feel free to edit
    vmx_file = vim.vm.FileInfo(logDirectory=None,
                               snapshotDirectory=None,
                               suspendDirectory=None,
                               vmPathName=datastore_path)

    config = vim.vm.ConfigSpec(name=vm_name, memoryMB=128, numCPUs=1,
                               files=vmx_file, guestId='dosGuest',
                               version='vmx-07')

    print("Creating VM {}...".format(vm_name))
    task = vm_folder.CreateVM_Task(config=config, pool=resource_pool)
    tasks.wait_for_tasks(service_instance, [task])


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
        marvel_public_key = input('Marvel public key: ').strip()

    if args.private_key_file:
        with open(args.private_key_file) as key_file:
            marvel_private_key = key_file.readline().strip()
    else:
        marvel_private_key = input('Marvel private key: ').strip()

    if args.disable_ssl_verification:
        service_instance = connect.SmartConnectNoSSL(host=args.host,
                                                     user=args.user,
                                                     pwd=args.password,
                                                     port=int(args.port))
    else:
        service_instance = connect.SmartConnect(host=args.host,
                                                user=args.user,
                                                pwd=args.password,
                                                port=int(args.port))
    if not service_instance:
        print("Could not connect to the specified host using specified "
              "username and password")
        return -1

    atexit.register(connect.Disconnect, service_instance)

    content = service_instance.RetrieveContent()
    # datacenter = get_obj(content, [vim.Datacenter], args.datacenter)
    vmfolder = get_obj(content, [vim.Folder], args.folder)
    resource_pool = get_obj(content, [vim.ResourcePool], args.resource_pool)

    print("Connecting to Marvel API and retrieving " + str(args.count) +
          " random character(s) ...")

    characters = get_marvel_characters(args.count,
                                       marvel_public_key,
                                       marvel_private_key)

    for name in characters:
        vm_name = 'MARVEL-' + name
        create_dummy_vm(vm_name, service_instance, vmfolder, resource_pool,
                        args.datastore)
        if args.opaque_network:
            vm = get_obj(content, [vim.VirtualMachine], vm_name)
            add_nic(service_instance, vm, args.opaque_network)
    return 0


# Start program
if __name__ == "__main__":
    main()
