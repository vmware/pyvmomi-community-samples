#!/usr/bin/env python
#
# Written by Juan Manuel Rey
# Github: https://github.com/jreypo
# Blog: http://blog.jreypo.io/
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# vSphere Python SDK script to force the HA reconfiguration in an ESXi host
# Tested with vSphere 6.0 U1
#

import argparse
import getpass
import atexit
import ssl

from pyVmomi import vim
from pyVim import connect
from tools import tasks


def get_args():
    """
    Retrieve script arguments
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('-s', '--host',
                        required=True, action='store',
                        help='vCenter Server address')

    parser.add_argument('-o', '--port',
                        type=int, default=443,
                        action='store', help='Port to connect to')

    parser.add_argument('-u', '--user',
                        required=True, action='store',
                        help='User name to use for the connection')

    parser.add_argument('-p', '--password',
                        required=False, action='store',
                        help='Password to use for the connection')

    parser.add_argument('-e', '--esx_host',
                        required=True, action='store',
                        help='Host to reconfigure')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password for user %s: ' % args.user)

    return args


def main():
    args = get_args()

    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.verify_mode = ssl.CERT_NONE

    service_instance = connect.SmartConnect(host=args.host,
                                            user=args.user,
                                            pwd=args.password,
                                            port=int(args.port),
                                            sslContext=context)
    if not service_instance:
        print("Unable to connect with the vCenter Server "
              "using the provided credentials")
        return -1

    atexit.register(connect.Disconnect, service_instance)

    content = service_instance.RetrieveContent()
    object_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                          [vim.HostSystem],
                                                          True)

    host_list = object_view.view
    object_view.Destroy()

    for host in host_list:
        if host.name == args.esx_host:
            esx = host

    print "Proceeding to execute operation 'Reconfigure for HA' in host %s" % \
          esx.name
    reconf_ha = esx.ReconfigureHostForDAS_Task()
    task = reconf_ha
    tasks.wait_for_tasks(service_instance, [task])
    print "Operation complete"

    return 0

# Main execution
if __name__ == "__main__":
    main()
