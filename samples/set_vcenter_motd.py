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

import requests
from tools import cli, service_instance
# Snippet borrowed from Michael Rice
# https://gist.github.com/michaelrice/a6794a017e349fc65d01
requests.packages.urllib3.disable_warnings()


# Demonstrates configuring the Message of the Day (MOTD) on vCenter Server

# Example output:
# > logged in to vcsa
# > Setting vCenter Server MOTD to "Hello from virtuallyGhetto"
# > logout

parser = cli.Parser()
parser.add_required_arguments(cli.Argument.MESSAGE)
args = parser.get_args()
si = service_instance.connect(args)

print("logged in to %s" % args.host)

print("Setting vCenter Server MOTD to \"%s\"" % args.message)
si.content.sessionManager.UpdateServiceMessage(message=args.message)

print("logout")
si.content.sessionManager.Logout()
