#!/usr/bin/env python
# VMware vSphere Python SDK
# Copyright (c) 2008-2013 VMware, Inc. All Rights Reserved.
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
Python program for changing the name of a datacenter using update_view_data
"""

import atexit

from pyVim import connect

import tools.cli as cli
import tools.folder as finders


def get_args():
    """
    Use the tools.cli methods and then add a few more arguments.
    """
    parser = cli.build_arg_parser()

    parser.add_argument('-d', '--datastore_name',
                        required=True,
                        action='store',
                        help='Name of the Datastore to rename.')

    args = parser.parse_args()

    return cli.prompt_for_password(args)

args = get_args()

# form a connection...
si = connect.SmartConnect(host=args.host,
                          user=args.user,
                          pwd=args.password,
                          port=args.port)

# doing this means you don't need to remember to disconnect your script/objects
atexit.register(connect.Disconnect, si)

ds_name = args.datastore_name

content = si.RetrieveContent()

datastore = content.rootFolder.find_child_by_name(ds_name)
print
print "name        : %s" % datastore.name
print "class       : %s" % datastore.__class__.__name__
print "url         : %s" % datastore.summary.url
print "type        : %s" % datastore.summary.type
print "connected host(s)"
for host in datastore.host:
    print "        %s is %s version %s" % (host.key.name,
                                           host.key.config.product.name,
                                           host.key.config.product.version)
print
