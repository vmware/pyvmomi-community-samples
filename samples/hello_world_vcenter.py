#!/usr/bin/env python
# VMware vSphere Python SDK
# Copyright (c) 2008-2021 VMware, Inc. All Rights Reserved.
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
Python program to authenticate and print
a friendly encouragement to joining the community!
"""

from pyVmomi import vmodl
from tools import cli, service_instance


def main():
    """
    Simple command-line program for listing the virtual machines on a system.
    """

    parser = cli.Parser()
    args = parser.get_args()
    si = service_instance.connect(args)

    try:
        print("\nHello World!\n")
        print("If you got here, you authenticted into vCenter.")
        print("The server is {}!".format(args.host))
        # NOTE (hartsock): only a successfully authenticated session has a
        # session key aka session id.
        session_id = si.content.sessionManager.currentSession.key
        print("current session id: {}".format(session_id))
        print("Well done!")
        print("\n")
        print("Download, learn and contribute back:")
        print("https://github.com/vmware/pyvmomi-community-samples")
        print("\n\n")

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
