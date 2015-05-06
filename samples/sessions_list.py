#!/usr/bin/env python
# VMware vSphere Python SDK
# Copyright (c) 2008-2014 VMware, Inc. All Rights Reserved.
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
import getpass

import pyVim.connect as connect

# Demonstrates some simple working with sessions actions. By common sense
# you should expect that the session is None when you've logged out and
# you will lose the ability to see any session ID. It would be a massive
# security hole to allow people to see these when they were not authenticated
# since the session ID is all you need to spoof another user's login.

# Example output:
# > logged in to vcsa
# > current pyVmomi session id: 523ea3ee-865b-fc7e-3486-bd380c3ab4a2
# > Listing all sessions I can see:
# > session 5205c9e7-8f79-6597-f1d9-e06583cb5089
# > session 523ea3ee-865b-fc7e-3486-bd380c3ab4a2
# > session 52500401-b1e7-bb05-c6b1-05d903d32dcb
# > session 5284cc12-f15c-363a-4455-ae8dbeb8bc3b
# > logout
# > current pyVmomi session: None


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
session_id = si.content.sessionManager.currentSession.key
print "current pyVmomi session id: %s" % session_id

print "Listing all sessions I can see:"
for session in si.content.sessionManager.sessionList:
    print "session %s" % session.key

print "logout"
si.content.sessionManager.Logout()

# The current session will be None after logout
session = si.content.sessionManager.currentSession
print "current pyVmomi session: %s" % session
