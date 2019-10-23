#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Written by Chris Arceneaux
# GitHub: https://github.com/carceneaux
# Email: carcenea@gmail.com
# Website: http://arsano.ninja
#
# Note: Example code For testing purposes only
#
# This code has been released under the terms of the Apache-2.0 license
# http://opensource.org/licenses/Apache-2.0

"""
Python program for retrieving a port group for both VSS and DVS
"""

import atexit

from tools import cli
from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim


def get_args():
    """
    Adds additional args for retrieving a port group

    -pg portgroupname
    """
    parser = cli.build_arg_parser()

    # because -p is reserved for 'password'
    parser.add_argument('-pg', '--portgroupname',
                        required=True,
                        help="Name of the port group")
    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)


def get_obj(content, vimtype, name):
    """
    Retrieves the managed object for the name and type specified

    Sample Usage:

    get_obj(content, [vim.Datastore], "Datastore Name")
    """
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            # print(Item: + c.name) # for debugging
            obj = c
            break
    if not obj:
        raise RuntimeError("Managed Object " + name + " not found.")
    return obj


def main():
    """
    Simple command-line program for retrieving a port group
    """

    args = get_args()

    try:
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

        atexit.register(connect.Disconnect, service_instance)

        content = service_instance.RetrieveContent()

        # searching for port group
        pg = get_obj(content, [vim.Network], args.portgroupname)
        print(pg)

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : {0}".format(error.msg))
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
