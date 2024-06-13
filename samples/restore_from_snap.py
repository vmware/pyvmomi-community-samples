#!/usr/bin/env python
#
# checks for a specific snapshot for a named VMs, and restores it
#
# Author: gavin.brebner@hpe.com
# Copyright Hewlett Packard Enterprise 2017

import atexit
import configargparse
import getpass
import re
import ssl
import sys
import time

from pyVim import connect
from pyVim.task import WaitForTask
from pyVmomi import vmodl, vim
from time import localtime, strftime

# creds etc can be stores in a file
DEFAULT_CONFIG_FILENAME = ".restore_config"

BASE_DESCRIPTION = 'Tool to automate reverting VMs to known snapshots' +\
                    ' via vSphere.'


def report(message):
    """
    Timestamped message output.
    :param message - message to display.
    """
    print strftime("%a, %d %b %Y %H:%M:%S", localtime()) + " : " + message


class EsxTalker(object):
    """
    Class that handles talking to ESX and holds the various utility methods
    """

    def __init__(self, args):
        """
        Initialise the EsxTalker.
        :param args - the params passed to the program, which must include
                      the username, password and host for the vSphere
        """
        self.args = args  # as there may be more than just the esx creds
        if self.args.debug:  # see :)
            report("Debug mode")
        # magic to disable SSL cert checking
        s = None
        if args.insecure:
            s = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            s.verify_mode = ssl.CERT_NONE
        # OK - let's get a connection
        try:
            self.svc_inst = connect.SmartConnect(host=args.host,
                                                 user=args.user,
                                                 pwd=args.password,
                                                 port=int(args.port),
                                                 sslContext=s)
            # incantation to close at the end
            atexit.register(connect.Disconnect, self.svc_inst)
            # verify that the connection has worked.
            self.sid = self.svc_inst.content.sessionManager.currentSession.key
            assert self.sid is not None, "Connection to ESX failed"
        except vmodl.MethodFault as error:
            report("Caught vmodl fault : " + error.msg)
            sys.exit(1)
        self.content = self.svc_inst.RetrieveContent()

    def get_obj(self, vimtype, name):
        """
        Get the vsphere object associated with a given text name
        :param vimtype - type of object searched for.
        :param name - name of item searched for.
        :return matching object or None
        """
        obj = None
        container = self.content.viewManager.CreateContainerView(
            self.content.rootFolder, vimtype, True)
        for c in container.view:
            if c.name == name:
                return c
        return None

    def get_vm_by_name(self, name):
        """
        Get the VM object for the VM with the given name
        :param name - exact name of target VM
        :return matching VM or None
        """
        return self.get_obj([vim.VirtualMachine], name)

    def get_snapshots(self, rootlist):
        """
        Starting from the root list, return
        a list of snapshots.
        :param rootlist - the VM snapshot rootlist
        :return list of snapshots
        """
        results = []
        for s in rootlist:
            results.append(s)
            results += self.get_snapshots(s.childSnapshotList)
        return results

    def find_matching_snapshot(self, snapshots, regex):
        """
        Return the list of existing snapshots filtered using
        a regex - which can be a simple substring expected to
        be found in the name field.
        :param snapshots - list of snapshots
        :param regex - string with an expression to re.search on.
        :return filtered list
        """
        if snapshots is None:
            return None
        if len(snapshots) < 1:
            return None
        return [s for s in snapshots if re.search(regex, s.name)]

    def create_snapshot(self,
                        vmname,
                        snapname,
                        description="",
                        dumpMem=False,
                        quiesce=False):
        """
        Create a snapshot of a named VM
        :param vmname - VM to be snapshotted
        :param snapname - name to use for snapshot
        """
        vm = self.get_vm_by_name(vmname)
        assert vm is not None, "Did not find specified VM!"
        report("Creating snapshot %s for %s ..." % (snapname, vmname))
        if self.args.debug:
            report("""
            DEBUG :
            WaitForTask(vm.CreateSnapshot(snap_name,
                                          description,
                                          dumpMem,
                                          quiesce))
            """)
        else:
            report("Starting to create snapshot ...")
            WaitForTask(vm.CreateSnapshot(snapname,
                                          description,
                                          dumpMem,
                                          quiesce))
            report("  done.")

    def revert_to_snap(self, vmname, snapnameregex):
        """
        Revert the named VM to the named snapshot
        :param vmname - the name of the VM
        :param snapnameregex - the search pattern for the chosen snapshot
        """
        report("Get snapshots from %s ..." % vmname)
        vm = self.get_vm_by_name(vmname)
        snaps = self.get_snapshots(vm.snapshot.rootSnapshotList)
        report("Finding snapshot ...")
        target_snap = self.find_matching_snapshot(snaps, snapnameregex)
        assert len(target_snap) == 1,\
            "More than one snap identified - confused!\n" +\
            "Please use a more unique string."
        report("Snap found matching name ...")
        thesnap2use = target_snap[0]
        assert thesnap2use is not None
        if self.args.debug:
            report("DEBUG : This task will cause the VM to revert")
        else:
            report("Reverting to snapshot ...")
            WaitForTask(thesnap2use.snapshot.RevertToSnapshot_Task())
            report("  done")


def get_args():
    """
    Get command line args from the user.
    Uses configargparse so can use combination of command line,
    config file and env vars
    """
    parser = configargparse.ArgParser(
        config_file_parser_class=configargparse.YAMLConfigFileParser,
        default_config_files=[DEFAULT_CONFIG_FILENAME],
        description=BASE_DESCRIPTION)
    parser.add_argument('-c', '--my-config',
                        required=False,
                        is_config_file=True,
                        help='config file path')
    parser.add_argument('-H', '--host',
                        required=True,
                        action='store',
                        help='vSphere instance to connect to')
    parser.add_argument('-P', '--port',
                        type=int,
                        default=443,
                        action='store',
                        help='Port to connect on')
    parser.add_argument('-u', '--user',
                        required=True,
                        env_var="VSPHERE_USER",
                        action='store',
                        help='User name to use for vSphere.')
    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        env_var="VSPHERE_PASSWORD",
                        help='Password to use for vSphere.')
    parser.add_argument('-v', '--vm_name',
                        required=True,
                        action='append',
                        default=[],
                        help='VM name - can be repeated')
    parser.add_argument('-s', '--snap_name',
                        required=True,
                        env_var="SNAP_NAME",
                        action='store',
                        help="String to use when searching snapshot names")
    parser.add_argument('-d', '--debug',
                        required=False,
                        action='store_true',
                        env_var="DEBUG",
                        help='Debug mode - do not do the revert')
    parser.add_argument('-S', '--save_first',
                        required=False,
                        action='store_true',
                        help='Before doing a revert, snapshot current state.')
    parser.add_argument('-i', '--insecure',
                        required=False,
                        action='store_true',
                        env_var='VSPHERE_INSECURE',
                        help='Insecure mode - ' +
                        'do not validate the SSL certificate')
    args = parser.parse_args()
    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password for host %s and user %s: ' %
                   (args.host, args.user))
    return args


def main():
    """
    """

    args = get_args()
    et = EsxTalker(args)

    report("Get VM by names =" + str(args.vm_name))
    for vmname in args.vm_name:
        if args.save_first:
            # prior to winding back, create a snapshot of now - just in case
            report("snapshotting prior to revert")
            new_snap_name = "%s_PREREVERT_%s" % (vmname, str(time.time()))
            description = "Snapshot prior to revert operation"
            et.create_snapshot(vmname, new_snap_name, description)
        # now do the revert
        et.revert_to_snap(vmname, args.snap_name)


if __name__ == "__main__":
    main()
