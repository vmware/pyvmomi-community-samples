#!/usr/bin/env python
#
# Written by JM Lopez
# GitHub: https://github.com/jm66
# Email: jm@jmll.me
# Website: http://jose-manuel.me
#
# Note: Example code For testing purposes only
#
# This code has been released under the terms of the Apache-2.0 license
# http://opensource.org/licenses/Apache-2.0
#

import atexit
import requests
from tools import cli
from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect

requests.packages.urllib3.disable_warnings()


def get_role_name_by_id(content, role_id):
    roles = content.authorizationManager.roleList
    return [role.name for role in roles if role.roleId == role_id]


def print_permissions(content, entity):
    auth_man = content.authorizationManager
    perms = auth_man.RetrieveEntityPermissions(entity=entity,
                                               inherited=True)
    permissions = [(perm.principal,
                    ','.join(get_role_name_by_id(content, perm.roleId)))
                   for perm in perms]
    print "Permissions           : {} [{}]".format(permissions[0][0],
                                                   permissions[0][1])
    if len(permissions) > 1:
        permissions.pop(0)
        for perm in permissions:
            print "                        {}, [{}]".format(perm[0],
                                                            perm[1])


def get_args():
    parser = cli.build_arg_parser()
    parser.add_argument('-n', '--name', required=True,
                        help="Name of the Object you want to change.")
    parser.add_argument('-t', '--type', required=True,
                        help='Object type, e.g. Network, VirtualMachine.',
                        type=str)
    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)


def get_obj(content, vim_type, name):
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vim_type, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def main():
    args = get_args()

    # connect to vc
    si = SmartConnect(
        host=args.host,
        user=args.user,
        pwd=args.password,
        port=args.port)
    # disconnect vc
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()
    # based on Benjamin Sherman
    # EZMOMI method (List available VMware objects)
    # https://github.com/snobear/ezmomi
    vim_obj = "vim.{}".format(args.type)
    print 'Searching for {} {}'.format(args.type, args.name)
    vim_obj = get_obj(content, [eval(vim_obj)], args.name)

    if vim_obj:
        print 'Name                  : {}'.format(args.name)
        print 'Object                : {}'.format(args.type)
        print_permissions(content, vim_obj)
    else:
        print "Object not found"

# start
if __name__ == "__main__":
    main()
