#!/usr/bin/env python
# William lam
# www.virtuallyghetto.com

"""
vSphere SDK for Python program for creating tiny VMs (1vCPU/128MB) with random
names using the Marvel Comics API
"""


import hashlib
import json
import random
import time
import requests
from pyVmomi import vim
from tools import cli, service_instance, tasks, pchelper
from add_nic_to_vm import add_nic

try:
    # pylint: disable=redefined-builtin
    input = raw_input
except NameError:
    pass


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


def create_dummy_vm(vm_name, si, vm_folder, resource_pool,
                    datastore):
    """Creates a dummy VirtualMachine with 1 vCpu, 128MB of RAM.

    :param name: String Name for the VirtualMachine
    :param si: ServiceInstance connection
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
    tasks.wait_for_tasks(si, [task])


def main():
    """
    Simple command-line program for creating Dummy VM based on Marvel character
    names
    """

    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.DATASTORE_NAME, cli.Argument.FOLDER_NAME,
                                  cli.Argument.RESOURCE_POOL, cli.Argument.OPAQUE_NETWORK_NAME)
    parser.add_custom_argument('--count',
                               type=int,
                               required=True,
                               action='store',
                               help='Number of VMs to create')
    # NOTE (hartsock): as a matter of good security practice, never ever
    # save a credential of any kind in the source code of a file. As a
    # matter of policy we want to show people good programming practice in
    # these samples so that we don't encourage security audit problems for
    # people in the future.
    parser.add_custom_argument('--public_key_file',
                               required=False,
                               action='store',
                               help='Name of the file holding your marvel public key,'
                                    ' the key should be the first only of the file. '
                                    'Set one up at developer.marvel.com/account')
    parser.add_custom_argument('--private_key_file',
                               required=False,
                               action='store',
                               help='Name of the file holding your marvel private '
                                    'key, the key should be the only line of the '
                                    'file. '
                                    'Set one up at developer.marvel.com/account')

    args = parser.get_args()
    si = service_instance.connect(args)

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

    content = si.RetrieveContent()
    vmfolder = pchelper.get_obj(content, [vim.Folder], args.folder_name)
    resource_pool = pchelper.get_obj(content, [vim.ResourcePool], args.resource_pool)

    print("Connecting to Marvel API and retrieving " + str(args.count) +
          " random character(s) ...")

    characters = get_marvel_characters(args.count,
                                       marvel_public_key,
                                       marvel_private_key)

    for name in characters:
        vm_name = 'MARVEL-' + name
        create_dummy_vm(vm_name, si, vmfolder, resource_pool,
                        args.datastore_name)
        if args.opaque_network_name:
            vm = pchelper.get_obj(content, [vim.VirtualMachine], vm_name)
            add_nic(si, vm, args.opaque_network_name)
    return 0


# Start program
if __name__ == "__main__":
    main()
