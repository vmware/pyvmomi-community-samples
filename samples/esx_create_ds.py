#!/usr/bin/env python
# Arvind Ayyangar


"""
vSphere Python SDK program to create a datastore give a device uuid
"""

import atexit
import time
import argparse
from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim
import requests

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def get_args():
    parser = argparse.ArgumentParser(
        description='Arguments for talking to vCenter')

    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='vSpehre service to connect to')

    parser.add_argument('-o', '--port',
                        type=int,
                        default=443,
                        action='store',
                        help='Port to connect on')

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='User name to use')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to use')

    parser.add_argument('--uuid',
                        required=True,
                        action='store',
                        help='uuid of disk')

    parser.add_argument('--dsname',
                        required=True,
                        action='store',
                        help='name of datastore')


    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password')

    return args


def createDatastore(si, uuid, dsname):
    dp="/vmfs/devices/disks/"+ str(uuid)
    content = si.RetrieveContent()
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
    for esx_host in container.view:
        try:
            hostdssystem = esx_host.configManager.datastoreSystem
            vmfs_ds_options = vim.host.DatastoreSystem.QueryVmfsDatastoreCreateOptions(hostdssystem, dp, 5)
            vmfs_ds_options[0].spec.vmfs.volumeName=dsname
            new_ds = vim.host.DatastoreSystem.CreateVmfsDatastore(hostdssystem, vmfs_ds_options[0].spec)
        except vim.fault.NotFound:
            print "Not found"
        except vim.fault.HostConfigFault:
            print "host config fault"
        except vmodl.fault.NotSupported:
            print "Not supported"
        except Exception as e:
            print "Unexpected error: %s" %e
        else:
            print "Datastore created"


def main():
    args = get_args()

    # connect this thing
    si = connect.SmartConnect(
        host=args.host,
        user=args.user,
        pwd=args.password,
        port=args.port)
    # disconnect this thing
    atexit.register(connect.Disconnect, si)

    createDatastore(si, args.uuid, args.dsname)


if __name__ == "__main__":
    main()
