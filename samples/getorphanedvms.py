#!/usr/bin/env python
"""
This module demonstrates how to find virtual machines that
exist on a datastore, but are not part of the inventory.
This can be useful to find orphaned virtual machines that
are still taking up datastore space, but not currently
being used.

Issues:
    Currently works with Windows based vCenter servers only.
    Still working on vCenter Server Appliance

Example:

      $./getorphanedvms.py -s 10.90.2.10 -u vcenter.svc -p password
"""

from pyVim.connect import SmartConnect
from pyVim.connect import Disconnect
from pyVmomi import vmodl
from pyVmomi import vim
import argparse
import atexit
import urllib2
import urlparse
import base64


VMX_PATH = []
DS_VM = {}
INV_VM = []


def updatevmx_path():
    """
    function to set the VMX_PATH global variable to null
    """
    global VMX_PATH
    VMX_PATH = []


def url_fix(s, charset='utf-8'):
    """
    function to fix any URLs that have spaces in them
    urllib for some reason doesn't like spaces
    function found on internet
    """
    if isinstance(s, unicode):
        s = s.encode(charset, 'ignore')
    scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
    path = urllib2.quote(path, '/%')
    qs = urllib2.quote(qs, ':&=')
    return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))


def get_args():
    """
    Supports the command-line arguments listed below.
    function to parse through args for connecting to ESXi host or
    vCenter server function taken from getallvms.py script
    from pyvmomi github repo
    """
    parser = argparse.ArgumentParser(
        description='Process args for retrieving all the Virtual Machines')
    parser.add_argument(
        '-s', '--host', required=True, action='store',
        help='Remote host to connect to')
    parser.add_argument(
        '-o', '--port', type=int, default=443, action='store',
        help='Port to connect on')
    parser.add_argument(
        '-u', '--user', required=True, action='store',
        help='User name to use when connecting to host')
    parser.add_argument(
        '-p', '--password', required=True, action='store',
        help='Password to use when connecting to host')
    args = parser.parse_args()
    return args


def find_vmx(dsbrowser, dsname, datacenter, fulldsname):
    """
    function to search for VMX files on any datastore that is passed to it
    """
    args = get_args()
    search = vim.HostDatastoreBrowserSearchSpec()
    search.matchPattern = "*.vmx"
    search_ds = dsbrowser.SearchDatastoreSubFolders_Task(dsname, search)
    while search_ds.info.state != "success":
        pass
    # results = search_ds.info.result
    # print results

    for rs in search_ds.info.result:
        dsfolder = rs.folderPath
        for f in rs.file:
            try:
                dsfile = f.path
                vmfold = dsfolder.split("]")
                vmfold = vmfold[1]
                vmfold = vmfold[1:]
                vmxurl = "https://%s/folder/%s%s?dcPath=%s&dsName=%s" % \
                         (args.host, vmfold, dsfile, datacenter, fulldsname)
                VMX_PATH.append(vmxurl)
            except Exception, e:
                print "Caught exception : " + str(e)
                return -1


def examine_vmx(dsname):
    """
    function to download any vmx file passed to it via the datastore browser
    and find the 'vc.uuid' and 'displayName'
    """
    args = get_args()
    try:
        for file_vmx in VMX_PATH:
            # print file_vmx

            username = args.user
            password = args.password
            request = urllib2.Request(url_fix(file_vmx))
            base64string = base64.encodestring(
                '%s:%s' % (username, password)).replace('\n', '')
            request.add_header("Authorization", "Basic %s" % base64string)
            result = urllib2.urlopen(request)
            vmxfile = result.readlines()
            mylist = []
            for a in vmxfile:
                mylist.append(a)
            for b in mylist:
                if b.startswith("displayName"):
                    dn = b
                if b.startswith("vc.uuid"):
                    vcid = b
            uuid = vcid.replace('"', "")
            uuid = uuid.replace("vc.uuid = ", "")
            uuid = uuid.strip("\n")
            uuid = uuid.replace(" ", "")
            uuid = uuid.replace("-", "")
            newdn = dn.replace('"', "")
            newdn = newdn.replace("displayName = ", "")
            newdn = newdn.strip("\n")
            vmfold = file_vmx.split("folder/")
            vmfold = vmfold[1].split("/")
            vmfold = vmfold[0]
            dspath = "%s/%s" % (dsname, vmfold)
            tempds_vm = [newdn, dspath]
            DS_VM[uuid] = tempds_vm

    except Exception, e:
        print "Caught exception : " + str(e)


def getvm_info(vm, depth=1):
    """
    Print information for a particular virtual machine or recurse
    into a folder with depth protection
    from the getallvms.py script from pyvmomi from github repo
    """
    maxdepth = 10

    # if this is a group it will have children. if it does,
    # recurse into them and then return

    if hasattr(vm, 'childEntity'):
        if depth > maxdepth:
            return
        vmlist = vm.childEntity
        for c in vmlist:
            getvm_info(c, depth+1)
        return
    if hasattr(vm, 'CloneVApp_Task'):
        vmlist = vm.vm
        for c in vmlist:
            getvm_info(c)
        return

    try:
        uuid = vm.config.instanceUuid
        uuid = uuid.replace("-", "")
        INV_VM.append(uuid)
    except Exception, e:
        print "Caught exception : " + str(e)
        return -1


def find_match(uuid):
    """
    function takes vc.uuid from the vmx file and the instance uuid from
    the inventory VM and looks for match if no match is found
    it is printed out.
    """
    a = 0
    for temp in INV_VM:
        if uuid == temp:
            a = a+1
    if a < 1:
        print DS_VM[uuid]


def main():
    """
    function runs all of the other functions. Some parts of this function
    are taken from the getallvms.py script from the pyvmomi gihub repo
    """
    args = get_args()
    try:
        si = None
        try:
            si = SmartConnect(host=args.host,
                              user=args.user,
                              pwd=args.password,
                              port=int(args.port))
        except IOError, e:
            pass

        if not si:
            print "Could not connect to the specified host using " \
                  "specified username and password"
            return -1

        atexit.register(Disconnect, si)

        content = si.RetrieveContent()
        datacenter = content.rootFolder.childEntity[0]
        datastores = datacenter.datastore
        vmfolder = datacenter.vmFolder
        vmlist = vmfolder.childEntity
        dsvmkey = []

        # each datastore found on ESXi host or vCenter is passed
        # to the find_vmx and examine_vmx functions to find all
        # VMX files and search them

        for ds in datastores:
            find_vmx(ds.browser, "[%s]" % ds.summary.name, datacenter.name,
                     ds.summary.name)
            examine_vmx(ds.summary.name)
            updatevmx_path()

        # each VM found in the inventory is passed to the getvm_info
        # function to get it's instanceuuid

        for vm in vmlist:
            getvm_info(vm)

        # each key from the DS_VM hashtable is added to a separate
        # list for comparison later

        for a in DS_VM.keys():
            dsvmkey.append(a)

        # each uuid in the dsvmkey list is passed to the find_match
        # function to look for a match

        print "The following virtual machine(s) do not exist in the " \
              "inventory, but exist on a datastore " \
              "(Display Name, Datastore/Folder name):"
        for match in dsvmkey:
            find_match(match)
        Disconnect(si)
    except vmodl.MethodFault, e:
        print "Caught vmodl fault : " + e.msg
        return -1
    except Exception, e:
        print "Caught exception : " + str(e)
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
