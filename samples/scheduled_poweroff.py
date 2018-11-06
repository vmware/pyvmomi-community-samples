#!/usr/bin/env python
"""
Written by Gaël Berthaud-Müller
Github : https://github.com/blacksponge

This code is released under the terms of the Apache 2
http://www.apache.org/licenses/LICENSE-2.0.html

Example code for using the task scheduler.
"""

import ssl
import atexit
from datetime import datetime

from pyVmomi import vim
from pyVim import connect

from tools import cli


def get_args():
    parser = cli.build_arg_parser()

    parser.add_argument('-d', '--date', required=False, action='store',
                        help='Date and time used to create the scheduled task '
                        'with the format d/m/Y H:M. If not specified execute '
                        'task immediately')
    parser.add_argument('-n', '--vmname', required=True, action='store',
                        help='VM name on which the action will be performed')
    args = parser.parse_args()
    return cli.prompt_for_password(args)


def main():
    args = get_args()

    dt = None
    if args.date:
        try:
            dt = datetime.strptime(args.date, '%d/%m/%Y %H:%M')
        except ValueError:
            print('Unrecognized date format')
            return -1

    sslContext = None

    if args.disable_ssl_verification:
        sslContext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        sslContext.verify_mode = ssl.CERT_NONE

    try:
        si = connect.SmartConnect(host=args.host,
                                  user=args.user,
                                  pwd=args.password,
                                  port=int(args.port),
                                  sslContext=sslContext)
    except vim.fault.InvalidLogin:
        print("Could not connect to the specified host using specified "
              "username and password")
        return -1

    atexit.register(connect.Disconnect, si)

    view = si.content.viewManager.CreateContainerView(si.content.rootFolder,
                                                      [vim.VirtualMachine],
                                                      True)
    vms = [vm for vm in view.view if vm.name == args.vmname]

    if not vms:
        print('VM not found')
        connect.Disconnect(si)
        return -1
    vm = vms[0]

    spec = vim.scheduler.ScheduledTaskSpec()
    spec.name = 'PowerOff vm %s' % args.vmname
    spec.description = ''
    spec.scheduler = vim.scheduler.OnceTaskScheduler()
    if dt:
        spec.scheduler.runAt = dt
    spec.action = vim.action.MethodAction()
    spec.action.name = vim.VirtualMachine.PowerOff
    spec.enabled = True

    si.content.scheduledTaskManager.CreateScheduledTask(vm, spec)


if __name__ == "__main__":
    main()
