# Written by Michael Rice
# Github: https://github.com/michaelrice
# Website: https://michaelrice.github.io/
# Blog: http://www.errr-online.com/
# This code has been released under the terms of the MIT licenses
# http://opensource.org/licenses/MIT
__author__ = 'errr'

import atexit

from pyVim import connect
from tools import cli


def setup_args():
    """
    Adds additional args to allow the vm uuid to
    be set.
    """
    parser = cli.build_arg_parser()
    # using j here because -u is used for user
    parser.add_argument('-j', '--uuid',
                        required=True,
                        help='UUID of the VirtualMachine you want to reboot.')
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
vm = si.content.searchIndex.FindByUuid(None, args.uuid, True, True)
if not vm:
    raise SystemExit("Unable to locate VirtualMachine.")

print "Found: {0}".format(vm.name)
print "The current powerState is: {0}".format(vm.runtime.powerState)
# This does not guarantee a reboot.
# It issues a command to the guest
# operating system asking it to perform a reboot.
# Returns immediately and does not wait for the guest
# operating system to complete the operation.
vm.RebootGuest()
print "A request to reboot the guest has been sent."
