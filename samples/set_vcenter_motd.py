#!/usr/bin/env python2.7
# William Lam
# wwww.virtuallyghetto.com
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

import argparse
import pyVim.connect as connect
import getpass
import requests
# Snippet borrowed from Michael Rice
# https://gist.github.com/michaelrice/a6794a017e349fc65d01
requests.packages.urllib3.disable_warnings()

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context

# Demonstrates configuring the Message of the Day (MOTD) on vCenter Server

# Example output:
# > logged in to vcsa
# > Setting vCenter Server MOTD to "Hello from virtuallyGhetto"
# > logout

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--host',
                    required=True,
                    action='store',
                    help='Remote host to connect to')

parser.add_argument('-u', '--user',
                    required=True,
                    action='store',
                    help='User name to use when connecting to host')

parser.add_argument('-p', '--password',
                    required=False,
                    action='store',
                    help='Password to use when connecting to host')

parser.add_argument('-o', '--port',
                    required=False,
                    action='store',
                    help="port to use, default 443", default=443)

parser.add_argument('-m', '--message',
                    required=True,
                    action='store',
                    help='Message to be used for VC MOTD')

args = parser.parse_args()
if args.password:
    password = args.password
else:
    password = getpass.getpass(
        prompt='Enter password for host %s and user %s: ' %
               (args.host, args.user))

si = connect.SmartConnect(host=args.host,
                          user=args.user,
                          pwd=password,
                          port=int(args.port))

print "logged in to %s" % args.host

print "Setting vCenter Server MOTD to \"%s\"" % args.message
si.content.sessionManager.UpdateServiceMessage(message=args.message)

print "logout"
si.content.sessionManager.Logout()
