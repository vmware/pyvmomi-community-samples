# Written by Michael Rice
# Github: https://github.com/michaelrice
# Website: https://michaelrice.github.io/
# Blog: http://www.errr-online.com/
# This code has been released under the terms of the MIT licenses
# http://opensource.org/licenses/MIT
__author__ = 'errr'

from tools import cli
from tools import taskops
from pyVim import connect

import atexit


def setup_args():
    """
    Adds additional args to allow the vm name or uuid to
    be set.
    """
    parser = cli.build_arg_parser()
    # using j here because -u is used for user
    parser.add_argument('-j', '--uuid',
                        help='UUID of the VirtualMachine you want to reboot.')
    parser.add_argument('-n', '--name',
                        help='DNS Name of the VirtualMachine you want to reboot.')
    parser.add_argument('-i', '--ip',
                        help='IP Address of the VirtualMachine you want to reboot')

    my_args = parser.parse_args()

    return cli.prompt_for_password(my_args)


args = setup_args()
si = None
try:
    si = connect.SmartConnect(host=args.host,
                              user=args.user,
                              pwd=args.password,
                              port=int(args.port))
    atexit.register(connect.Disconnect, si)
except IOError, e:
    pass

if not si:
    raise SystemExit("Unable to connect to host with supplied info.")
vm = None
if args.uuid:
    vm = si.content.searchIndex.FindByUuid(None, args.uuid, True)
elif args.name:
    vm = si.content.searchIndex.FindByDnsName(None, args.name, True)
elif args.ip:
    vm = si.content.searchIndex.FindByIp(None, args.ip, True)

if vm is None:
    raise SystemExit("Unable to locate VirtualMachine.")

print "Found: {0}".format(vm.name)
print "The current powerState is: {0}".format(vm.runtime.powerState)
task = vm.ResetVM_Task()
taskops.wait_for_tasks([task], si)
print "its done."