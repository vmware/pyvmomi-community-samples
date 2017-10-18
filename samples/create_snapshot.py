# Copyright 2015 Michael Rice <michael@michaelrice.org>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from __future__ import print_function

import atexit

import requests

from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect

from tools import cli

requests.packages.urllib3.disable_warnings()


def setup_args():
    parser = cli.build_arg_parser()
    parser.add_argument('-j', '--uuid', required=True,
                        help="UUID of the VirtualMachine you want to find."
                             " If -i is not used BIOS UUID assumed.")
    parser.add_argument('-i', '--instance', required=False,
                        action='store_true',
                        help="Flag to indicate the UUID is an instance UUID")
    parser.add_argument('-d', '--description', required=False,
                        help="Description for the snapshot")
    parser.add_argument('-n', '--name', required=True,
                        help="Name for the Snapshot")
    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)


args = setup_args()
si = None
instance_search = False
try:
    if args.disable_ssl_verification:
        si = SmartConnectNoSSL(host=args.host,
                               user=args.user,
                               pwd=args.password,
                               port=int(args.port))
    else:
        si = SmartConnect(host=args.host,
                          user=args.user,
                          pwd=args.password,
                          port=int(args.port))

    atexit.register(Disconnect, si)
except IOError:
    pass

if not si:
    raise SystemExit("Unable to connect to host with supplied info.")
if args.instance:
    instance_search = True
vm = si.content.searchIndex.FindByUuid(None, args.uuid, True, instance_search)

if vm is None:
    raise SystemExit("Unable to locate VirtualMachine.")

desc = None
if args.description:
    desc = args.description

task = vm.CreateSnapshot_Task(name=args.name,
                              description=desc,
                              memory=True,
                              quiesce=False)
print("Snapshot Completed.")
del vm
vm = si.content.searchIndex.FindByUuid(None, args.uuid, True, instance_search)
snap_info = vm.snapshot

tree = snap_info.rootSnapshotList
while tree[0].childSnapshotList is not None:
    print("Snap: {0} => {1}".format(tree[0].name, tree[0].description))
    if len(tree[0].childSnapshotList) < 1:
        break
    tree = tree[0].childSnapshotList
