# VMware vSphere Python SDK Community Samples Addons
# Copyright (c) 2014-2021 VMware, Inc. All Rights Reserved.
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
This module implements simple helper functions for python samples
"""
import argparse
import getpass

__author__ = "VMware, Inc."


class Parser:
    """
    Samples specific argument parser.
    Wraps argparse to ease the setup of argument requirements for the samples.

    Example:
        parser = cli.Parser()
        parser.add_required_arguments(cli.Argument.VM_NAME)
        parser.add_optional_arguments(cli.Argument.DATACENTER_NAME, cli.Argument.NIC_NAME)
        parser.add_custom_argument(
            '--disk-number', required=True, help='Disk number to change mode.')
        args = parser.get_args()
    """

    def __init__(self):
        """
        Defines two arguments groups.
        One for the standard arguments and one for sample specific arguments.
        The standard group cannot be extended.
        """
        self._parser = argparse.ArgumentParser(description='Arguments for talking to vCenter')
        self._standard_args_group = self._parser.add_argument_group('standard arguments')
        self._specific_args_group = self._parser.add_argument_group('sample-specific arguments')

        # because -h is reserved for 'help' we use -s for service
        self._standard_args_group.add_argument('-s', '--host',
                                               required=True,
                                               action='store',
                                               help='vSphere service address to connect to')

        # because we want -p for password, we use -o for port
        self._standard_args_group.add_argument('-o', '--port',
                                               type=int,
                                               default=443,
                                               action='store',
                                               help='Port to connect on')

        self._standard_args_group.add_argument('-u', '--user',
                                               required=True,
                                               action='store',
                                               help='User name to use when connecting to host')

        self._standard_args_group.add_argument('-p', '--password',
                                               required=False,
                                               action='store',
                                               help='Password to use when connecting to host')

        self._standard_args_group.add_argument('-nossl', '--disable-ssl-verification',
                                               required=False,
                                               action='store_true',
                                               help='Disable ssl host certificate verification')

    def get_args(self):
        """
        Supports the command-line arguments needed to form a connection to vSphere.
        """
        args = self._parser.parse_args()
        return self._prompt_for_password(args)

    def _add_sample_specific_arguments(self, is_required: bool, *args):
        """
        Add an argument to the "sample specific arguments" group
        Requires a predefined argument from the Argument class.
        """
        for arg in args:
            name_or_flags = arg["name_or_flags"]
            options = arg["options"]
            options["required"] = is_required
            self._specific_args_group.add_argument(*name_or_flags, **options)

    def add_required_arguments(self, *args):
        """
        Add a required argument to the "sample specific arguments" group
        Requires a predefined argument from the Argument class.
        """
        self._add_sample_specific_arguments(True, *args)

    def add_optional_arguments(self, *args):
        """
        Add an optional argument to the "sample specific arguments" group.
        Requires a predefined argument from the Argument class.
        """
        self._add_sample_specific_arguments(False, *args)

    def add_custom_argument(self, *name_or_flags, **options):
        """
        Uses ArgumentParser.add_argument() to add a full definition of a command line argument
        to the "sample specific arguments" group.
        https://docs.python.org/3/library/argparse.html#the-add-argument-method
        """
        self._specific_args_group.add_argument(*name_or_flags, **options)

    def set_epilog(self, epilog):
        """
        Text to display after the argument help
        """
        self._parser.epilog = epilog

    def _prompt_for_password(self, args):
        """
        if no password is specified on the command line, prompt for it
        """
        if not args.password:
            args.password = getpass.getpass(
                prompt='"--password" not provided! Please enter password for host %s and user %s: '
                       % (args.host, args.user))
        return args


class Argument:
    """
    Predefined arguments to use in the Parser

    Example:
        parser = cli.Parser()
        parser.add_optional_arguments(cli.Argument.VM_NAME)
        parser.add_optional_arguments(cli.Argument.DATACENTER_NAME, cli.Argument.NIC_NAME)
    """
    def __init__(self):
        pass

    UUID = {
        'name_or_flags': ['--uuid'],
        'options': {'action': 'store', 'help': 'UUID of an entity (VirtualMachine or HostSystem)'}
    }
    VM_NAME = {
        'name_or_flags': ['-v', '--vm-name'],
        'options': {'action': 'store', 'help': 'Name of the vm'}
    }
    VM_IP = {
        'name_or_flags': ['--vm-ip'],
        'options': {'action': 'store', 'help': 'IP of the vm'}
    }
    VM_MAC = {
        'name_or_flags': ['-mac', '--vm-mac'],
        'options': {'action': 'store', 'help': 'Mac address of the VM'}
    }
    VM_USER = {
        'name_or_flags': ['--vm-user'],
        'options': {'action': 'store', 'help': 'virtual machine user name'}
    }
    VM_PASS = {
        'name_or_flags': ['--vm-password'],
        'options': {'action': 'store', 'help': 'virtual machine password'}
    }
    ESX_NAME = {
        'name_or_flags': ['-e', '--esx-name'],
        'options': {'action': 'store', 'help': 'Esx name'}
    }
    ESX_IP = {
        'name_or_flags': ['--esx-ip'],
        'options': {'action': 'store', 'help': 'Esx ip'}
    }
    ESX_NAME_REGEX = {
        'name_or_flags': ['--esx-name-regex'],
        'options': {'action': 'store', 'help': 'Esx name regex'}
    }
    DNS_NAME = {
        'name_or_flags': ['--dns-name'],
        'options': {'action': 'store', 'help': 'DNS name'}
    }
    NAME = {
        'name_or_flags': ['-n', '--name'],
        'options': {'action': 'store', 'help': 'Name of the entity'}
    }
    NEW_NAME = {
        'name_or_flags': ['-r', '--new-name'],
        'options': {'action': 'store', 'help': 'New name of the entity.'}
    }
    DATACENTER_NAME = {
        'name_or_flags': ['--datacenter-name'],
        'options': {'action': 'store', 'help': 'Datacenter name'}
    }
    DATASTORE_NAME = {
        'name_or_flags': ['--datastore-name'],
        'options': {'action': 'store', 'help': 'Datastore name'}
    }
    CLUSTER_NAME = {
        'name_or_flags': ['--cluster-name'],
        'options': {'action': 'store', 'help': 'Cluster name'}
    }
    FOLDER_NAME = {
        'name_or_flags': ['--folder-name'],
        'options': {'action': 'store', 'help': 'Folder name'}
    }
    TEMPLATE = {
        'name_or_flags': ['--template'],
        'options': {'action': 'store', 'help': 'Name of the template/VM'}
    }
    VMFOLDER = {
        'name_or_flags': ['--vm-folder'],
        'options': {'action': 'store', 'help': 'Name of the VMFolder'}
    }
    DATASTORECLUSTER_NAME = {
        'name_or_flags': ['--datastorecluster-name'],
        'options': {'action': 'store', 'help': 'Datastorecluster (DRS Storagepod)'}
    }
    RESOURCE_POOL = {
        'name_or_flags': ['--resource-pool'],
        'options': {'action': 'store', 'help': 'Resource pool name'}
    }
    POWER_ON = {
        'name_or_flags': ['--power-on'],
        'options': {'action': 'store_true', 'help': 'power on the VM'}
    }
    LANGUAGE = {
        'name_or_flags': ['--language'],
        'options': {'action': 'store', 'default': 'English', 'help': 'Language your vcenter used.'}
    }
    VIHOST = {
        'name_or_flags': ['--vihost'],
        'options': {'action': 'store',
                    'help': 'Name/ip address of ESXi host as seen in vCenter Server'}
    }
    DVS_PORT_GROUP_NAME = {
        'name_or_flags': ['--dvs-pg-name'],
        'options': {'action': 'store', 'help': '"Name of the distributed port group'}
    }
    DVS_NAME = {
        'name_or_flags': ['--dvs-name'],
        'options': {'action': 'store', 'help': 'Name of the distributed virtual switch'}
    }
    OPAQUE_NETWORK_NAME = {
        'name_or_flags': ['--opaque-network-name'],
        'options': {'action': 'store', 'help': 'Name of an opaque network'}
    }
    FIRST_CLASS_DISK_NAME = {
        'name_or_flags': ['--fcd-name'],
        'options': {'action': 'store', 'help': 'First Class Disk name'}
    }
    DISK_TYPE = {
        'name_or_flags': ['--disk-type'],
        'options': {'action': 'store',
                    'default': 'thin', 'choices': ['thick', 'thin'], 'help': 'thick or thin'}
    }
    DISK_SIZE = {
        'name_or_flags': ['--disk-size'],
        'options': {'action': 'store', 'help': 'disk size, in GB, to add to the VM'}
    }
    PORT_GROUP = {
        'name_or_flags': ['-g', '--port-group'],
        'options': {'action': 'store', 'help': 'Name of port group'}
    }
    NETWORK_NAME = {
        'name_or_flags': ['--network-name'],
        'options': {'action': 'store', 'help': 'Name of network'}
    }
    VSWITCH_NAME = {
        'name_or_flags': ['-w', '--vswitch-name'],
        'options': {'action': 'store', 'help': 'vSwitch name'}
    }
    LOCAL_FILE_PATH = {
        'name_or_flags': ['--local-file-path'],
        'options': {'action': 'store', 'help': 'Local disk path to file'}
    }
    REMOTE_FILE_PATH = {
        'name_or_flags': ['--remote-file-path'],
        'options': {'action': 'store', 'help': 'Path on datastore or vm or other entity to file'}
    }
    VLAN_ID = {
        'name_or_flags': ['--vlan-id'],
        'options': {'action': 'store', 'help': 'Vlan ID'}
    }
    DEVICE_NAME = {
        'name_or_flags': ['--device-name'],
        'options': {'action': 'store', 'help': 'The device name. Might look like '
                                               '"/vmfs/devices/disks/naa.*". '
                                               'See vim.vm.device.VirtualDisk.'
                                               'RawDiskMappingVer1BackingInfo documentation.'}}
    DISK_MODE = {
        'name_or_flags': ['--disk-mode'],
        'options': {'action': 'store',
                    'default': 'independent_persistent',
                    'choices': [
                        'append',
                        'independent_nonpersistent',
                        'independent_persistent',
                        'nonpersistent',
                        'persistent',
                        'undoable'],
                    'help': 'See vim.vm.device.VirtualDiskOption.DiskMode documentation.'}}

    COMPATIBILITY_MODE = {
        'name_or_flags': ['--disk-compatibility-mode'],
        'options': {'action': 'store',
                    'default': 'virtualMode',
                    'choices': ['physicalMode', 'virtualMode'],
                    'help': 'See vim.vm.device.VirtualDiskOption.CompatibilityMode documentation.'}}

    ISO = {
        'name_or_flags': ['--iso'],
        'options': {'action': 'store',
                    'help': 'ISO to use in test. Use datastore path format. '
                            'E.g. [datastore1] path/to/file.iso'}
    }
    NIC_NAME = {
        'name_or_flags': ['--nic-name'],
        'options': {'action': 'store', 'help': 'NIC number.'}
    }
    NIC_UNIT_NUMBER = {
        'name_or_flags': ['--nic-unitnumber'],
        'options': {'action': 'store', 'type': int, 'help': 'NIC number.'}
    }
    NIC_STATE = {
        'name_or_flags': ['--nic-state'],
        'options': {'action': 'store', 'choices': ['delete', 'disconnect', 'connect'],
                    'help': 'NIC number.'}
    }
    VMDK_PATH = {
        'name_or_flags': ['--vmdk-path'],
        'options': {'action': 'store', 'help': 'Path of the VMDK file.'}
    }
    OVA_PATH = {
        'name_or_flags': ['--ova-path'],
        'options': {'action': 'store', 'help': 'Path to the OVA file.'}
    }
    OVF_PATH = {
        'name_or_flags': ['--ovf-path'],
        'options': {'action': 'store', 'help': 'Path to the OVF file.'}
    }
    DATE = {
        'name_or_flags': ['--date'],
        'options': {'action': 'store', 'help': 'Date and time with the format d/m/Y H:M'}
    }
    MINUTES = {
        'name_or_flags': ['--minutes'],
        'options': {'action': 'store', 'help': 'time in minutes'}
    }
    MESSAGE = {
        'name_or_flags': ['-m', '--message'],
        'options': {'action': 'store', 'help': 'Message'}
    }

    SNAPSHOT_OPERATION = {
        'name_or_flags': ['-op', '--snapshot-operation'],
        'options': {'action': 'store',
                    'choices':
                        ['create', 'remove', 'revert', 'list_all', 'list_current', 'remove_all'],
                    'help': 'Snapshot operation'}
    }
    SNAPSHOT_NAME = {
        'name_or_flags': ['--snapshot-name'],
        'options': {'action': 'store', 'help': 'Snapshot name'}
    }
    STORAGE_POLICY_NAME = {
        'name_or_flags': ['--storage-policy-name'],
        'options': {'action': 'store', 'metavar': 'string', 'help': 'Storage policy name'}
    }
    ASSUME_INPUT = {
        'name_or_flags': ['--assume-input'],
        'options': {'action': 'store', 'help': 'Assume user input'}
    }
    SSL_KEY = {
        'name_or_flags': ['--ssl-key'],
        'options': {'action': 'store', 'help': 'absolute location of the private key file'}
    }
    SSL_CERT = {
        'name_or_flags': ['--ssl-cert'],
        'options': {'action': 'store', 'help': 'absolute location of the certificate file'}
    }


def prompt_y_n_question(question, default="no"):
    """ based on:
        http://code.activestate.com/recipes/577058/
    :param question: Question to ask
    :param default: No
    :return: True/False
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("Invalid default answer: '{}'".format(default))

    while True:
        print(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            print("Please, respond with 'yes' or 'no' or 'y' or 'n'.")
