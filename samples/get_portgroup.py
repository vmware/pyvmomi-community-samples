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

from tools import cli, pchelper, service_instance
from pyVmomi import vmodl, vim


def main():
    """
    Simple command-line program for retrieving a port group
    """

    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.PORT_GROUP)
    args = parser.get_args()
    si = service_instance.connect(args)

    try:
        content = si.RetrieveContent()

        # searching for port group
        port_group = pchelper.get_obj(content, [vim.Network], args.port_group)
        print(port_group)

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : {0}".format(error.msg))
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
