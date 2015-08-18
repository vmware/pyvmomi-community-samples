#!/usr/bin/python
# Luis San Martin - github.com/pathcl
# Attempts to get current processes on a given VM (uuid) and outputs to a csv
# Through pyvmomi and vmware-tools
# Further reference can be found at
# https://www.vmware.com/support/developer/converter-sdk/conv50_apireference/vim.vm.guest.ProcessManager.html

from __future__ import print_function
from pyVim import connect
from pyVmomi import vim

import tools.cli as cli
import atexit
import pandas as pd

# Setup args function and get arguments


def setup_args():
    parser = cli.build_arg_parser()
    parser.add_argument('-uuid', '--uuid',
                        help='file of uuid',
                        required=True)
    parser.add_argument('-vmpass', '--vmpass',
                        help='vm passwd',
                        required=True)
    parser.add_argument('-vmuser', '--vmuser',
                        help='file of uuid',
                        required=True)
    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)


ARGS = setup_args()


try:
    SI = connect.SmartConnect(host=ARGS.host,
                              user=ARGS.user,
                              pwd=ARGS.password,
                              port=ARGS.port)

    content = SI.RetrieveContent()
    atexit.register(connect.Disconnect, SI)
    creds = vim.vm.guest.NamePasswordAuthentication(username=ARGS.vmuser,
                                                    password=ARGS.vmpass)

except IOError:
    pass

# Main function which tries to find VM through UUID


def main(vm):
    vm = content.searchIndex.FindByUuid(None, ARGS.uuid, True, True)
    procs = content.guestOperationsManager.processManager.ListProcesses(vm,
                                                                        creds)
    vmprocs = [(proc.owner, proc.pid, proc.cmdLine) for proc in procs]
    print("Process for {0}".format(vm.name))
    print("")
    csv = pd.DataFrame(vmprocs)
    csv.to_csv(vm.name + '.csv', index=False, header=False)
    print(csv)

if __name__ == '__main__':
    main(ARGS.uuid)
