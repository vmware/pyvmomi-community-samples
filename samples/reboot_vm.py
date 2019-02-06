#!/usr/bin/env python
#
# Written by Michael Rice
# Github: https://github.com/michaelrice
# Website: https://michaelrice.github.io/
# Blog: http://www.errr-online.com/
#
# This code is released under the terms of the Apache 2
# http://www.apache.org/licenses/LICENSE-2.0.html
#
# Example script to reboot a VirtualMachine

import atexit

from pyVim import connect

from tools import cli
from tools import tasks


def setup_args():
    """Adds additional ARGS to allow the vm name or uuid to
    be set.
    """
    parser = cli.build_arg_parser()
    # using j here because -u is used for user
    parser.add_argument('-j', '--uuid',
                        help='UUID of the VirtualMachine you want to reboot.')
    parser.add_argument('-n', '--name',
                        help='DNS Name of the VirtualMachine you want to '
                             'reboot.')
    parser.add_argument('-i', '--ip',
                        help='IP Address of the VirtualMachine you want to '
                             'reboot')

    my_args = parser.parse_args()

    return cli.prompt_for_password(my_args)


ARGS = setup_args()
SI = None
try:
    if ARGS.disable_ssl_verification:
        SI = connect.SmartConnectNoSSL(host=ARGS.host,
                                       user=ARGS.user,
                                       pwd=ARGS.password,
                                       port=ARGS.port)
    else:
        SI = connect.SmartConnect(host=ARGS.host,
                                  user=ARGS.user,
                                  pwd=ARGS.password,
                                  port=ARGS.port)
    atexit.register(connect.Disconnect, SI)
except IOError as ex:
    pass

if not SI:
    raise SystemExit("Unable to connect to host with supplied info.")
VM = None
if ARGS.uuid:
    VM = SI.content.searchIndex.FindByUuid(None, ARGS.uuid,
                                           True,
                                           True)
elif ARGS.name:
    VM = SI.content.searchIndex.FindByDnsName(None, ARGS.name,
                                              True)
elif ARGS.ip:
    VM = SI.content.searchIndex.FindByIp(None, ARGS.ip, True)

if VM is None:
    raise SystemExit("Unable to locate VirtualMachine.")

print("Found: {0}".format(VM.name))
print("The current powerState is: {0}".format(VM.runtime.powerState))
TASK = VM.ResetVM_Task()
tasks.wait_for_tasks(SI, [TASK])
print("its done.")
