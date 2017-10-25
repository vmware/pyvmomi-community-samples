#!/usr/bin/env python
"""
Written by Nathan Prziborowski
Github: https://github.com/prziborowski

This code is released under the terms of the Apache 2
http://www.apache.org/licenses/LICENSE-2.0.html

Deploy an ova file either from a local path or a URL.
Most of the functionality is similar to ovf except that
that an OVA file is a "tarball" so tarfile module is leveraged.

"""
import atexit
import os
import os.path
import ssl
import sys
import tarfile
import time

from threading import Timer
from argparse import ArgumentParser
from getpass import getpass
from six.moves.urllib.request import Request, urlopen

from tools import cli

from pyVim.connect import SmartConnectNoSSL, Disconnect
from pyVmomi import vim, vmodl

__author__ = 'prziborowski'


def setup_args():
    parser = cli.build_arg_parser()
    parser.add_argument('--ova-path',
                        help='Path to the OVA file, can be local or a URL.')
    parser.add_argument('-d', '--datacenter',
                        help='Name of datacenter to search on. '
                             'Defaults to first.')
    parser.add_argument('-r', '--resource-pool',
                        help='Name of resource pool to use. '
                             'Defaults to largest memory free.')
    parser.add_argument('-ds', '--datastore',
                        help='Name of datastore to use. '
                             'Defaults to largest free space in datacenter.')
    return cli.prompt_for_password(parser.parse_args())


def main():
    args = setup_args()
    try:
        si = SmartConnectNoSSL(host=args.host,
                               user=args.user,
                               pwd=args.password,
                               port=args.port)
        atexit.register(Disconnect, si)
    except:
        print("Unable to connect to %s" % args.host)
        return 1

    if args.datacenter:
        dc = get_dc(si, args.datacenter)
    else:
        dc = si.content.rootFolder.childEntity[0]

    if args.resource_pool:
        rp = get_rp(si, dc, args.resource_pool)
    else:
        rp = get_largest_free_rp(si, dc)

    if args.datastore:
        ds = get_ds(dc, args.datastore)
    else:
        ds = get_largest_free_ds(dc)

    ovf_handle = OvfHandler(args.ova_path)

    ovfManager = si.content.ovfManager
    # CreateImportSpecParams can specify many useful things such as
    # diskProvisioning (thin/thick/sparse/etc)
    # networkMapping (to map to networks)
    # propertyMapping (descriptor specific properties)
    cisp = vim.OvfManager.CreateImportSpecParams()
    cisr = ovfManager.CreateImportSpec(ovf_handle.get_descriptor(),
                                       rp, ds, cisp)

    # These errors might be handleable by supporting the parameters in
    # CreateImportSpecParams
    if len(cisr.error):
        print("The following errors will prevent import of this OVA:")
        for error in cisr.error:
            print("%s" % error)
        return 1

    ovf_handle.set_spec(cisr)

    lease = rp.ImportVApp(cisr.importSpec, dc.vmFolder)
    while lease.state == vim.HttpNfcLease.State.initializing:
        print("Waiting for lease to be ready...")
        time.sleep(1)

    if lease.state == vim.HttpNfcLease.State.error:
        print("Lease error: %s" % lease.error)
        return 1
    if lease.state == vim.HttpNfcLease.State.done:
        return 0

    print("Starting deploy...")
    return ovf_handle.upload_disks(lease, args.host)


def get_dc(si, name):
    """
    Get a datacenter by its name.
    """
    for dc in si.content.rootFolder.childEntity:
        if dc.name == name:
            return dc
    raise Exception('Failed to find datacenter named %s' % name)


def get_rp(si, dc, name):
    """
    Get a resource pool in the datacenter by its names.
    """
    viewManager = si.content.viewManager
    containerView = viewManager.CreateContainerView(dc, [vim.ResourcePool],
                                                    True)
    try:
        for rp in containerView.view:
            if rp.name == name:
                return rp
    finally:
        containerView.Destroy()
    raise Exception("Failed to find resource pool %s in datacenter %s" %
                    (name, dc.name))


def get_largest_free_rp(si, dc):
    """
    Get the resource pool with the largest unreserved memory for VMs.
    """
    viewManager = si.content.viewManager
    containerView = viewManager.CreateContainerView(dc, [vim.ResourcePool],
                                                    True)
    largestRp = None
    unreservedForVm = 0
    try:
        for rp in containerView.view:
            if rp.runtime.memory.unreservedForVm > unreservedForVm:
                largestRp = rp
                unreservedForVm = rp.runtime.memory.unreservedForVm
    finally:
        containerView.Destroy()
    if largestRp is None:
        raise Exception("Failed to find a resource pool in dc %s" % dc.name)
    return largestRp


def get_ds(dc, name):
    """
    Pick a datastore by its name.
    """
    for ds in dc.datastore:
        try:
            if ds.name == name:
                return ds
        except:  # Ignore datastores that have issues
            pass
    raise Exception("Failed to find %s on datacenter %s" % (name, dc.name))


def get_largest_free_ds(dc):
    """
    Pick the datastore that is accessible with the largest free space.
    """
    largest = None
    largestFree = 0
    for ds in dc.datastore:
        try:
            freeSpace = ds.summary.freeSpace
            if freeSpace > largestFree and ds.summary.accessible:
                largestFree = freeSpace
                largest = ds
        except:  # Ignore datastores that have issues
            pass
    if largest is None:
        raise Exception('Failed to find any free datastores on %s' % dc.name)
    return largest


def get_tarfile_size(tarfile):
    """
    Determine the size of a file inside the tarball.
    If the object has a size attribute, use that. Otherwise seek to the end
    and report that.
    """
    if hasattr(tarfile, 'size'):
        return tarfile.size
    size = tarfile.seek(0, 2)
    tarfile.seek(0, 0)
    return size


class OvfHandler(object):
    """
    OvfHandler handles most of the OVA operations.
    It processes the tarfile, matches disk keys to files and
    uploads the disks, while keeping the progress up to date for the lease.
    """
    def __init__(self, ovafile):
        """
        Performs necessary initialization, opening the OVA file,
        processing the files and reading the embedded ovf file.
        """
        self.handle = self._create_file_handle(ovafile)
        self.tarfile = tarfile.open(fileobj=self.handle)
        ovffilename = list(filter(lambda x: x.endswith(".ovf"),
                                  self.tarfile.getnames()))[0]
        ovffile = self.tarfile.extractfile(ovffilename)
        self.descriptor = ovffile.read().decode()

    def _create_file_handle(self, entry):
        """
        A simple mechanism to pick whether the file is local or not.
        This is not very robust.
        """
        if os.path.exists(entry):
            return FileHandle(entry)
        else:
            return WebHandle(entry)

    def get_descriptor(self):
        return self.descriptor

    def set_spec(self, spec):
        """
        The import spec is needed for later matching disks keys with
        file names.
        """
        self.spec = spec

    def get_disk(self, fileItem, lease):
        """
        Does translation for disk key to file name, returning a file handle.
        """
        ovffilename = list(filter(lambda x: x == fileItem.path,
                                  self.tarfile.getnames()))[0]
        return self.tarfile.extractfile(ovffilename)

    def get_device_url(self, fileItem, lease):
        for deviceUrl in lease.info.deviceUrl:
            if deviceUrl.importKey == fileItem.deviceId:
                return deviceUrl
        raise Exception("Failed to find deviceUrl for file %s" % fileItem.path)

    def upload_disks(self, lease, host):
        """
        Uploads all the disks, with a progress keep-alive.
        """
        self.lease = lease
        try:
            self.start_timer()
            for fileItem in self.spec.fileItem:
                self.upload_disk(fileItem, lease, host)
            lease.Complete()
            print("Finished deploy successfully.")
            return 0
        except vmodl.MethodFault as e:
            print("Hit an error in upload: %s" % e)
            lease.Abort(e)
        except Exception as e:
            print("Lease: %s" % lease.info)
            print("Hit an error in upload: %s" % e)
            lease.Abort(vmodl.fault.SystemError(reason=str(e)))
            raise
        return 1

    def upload_disk(self, fileItem, lease, host):
        """
        Upload an individual disk. Passes the file handle of the
        disk directly to the urlopen request.
        """
        ovffile = self.get_disk(fileItem, lease)
        if ovffile is None:
            return
        deviceUrl = self.get_device_url(fileItem, lease)
        url = deviceUrl.url.replace('*', host)
        headers = {'Content-length': get_tarfile_size(ovffile)}
        if hasattr(ssl, '_create_unverified_context'):
            sslContext = ssl._create_unverified_context()
        else:
            sslContext = None
        req = Request(url, ovffile, headers)
        urlopen(req, context=sslContext)

    def start_timer(self):
        """
        A simple way to keep updating progress while the disks are transferred.
        """
        Timer(5, self.timer).start()

    def timer(self):
        """
        Update the progress and reschedule the timer if not complete.
        """
        try:
            prog = self.handle.progress()
            self.lease.Progress(prog)
            if self.lease.state not in [vim.HttpNfcLease.State.done,
                                        vim.HttpNfcLease.State.error]:
                self.start_timer()
            sys.stderr.write("Progress: %d%%\r" % prog)
        except:  # Any exception means we should stop updating progress.
            pass


class FileHandle(object):
    def __init__(self, filename):
        self.filename = filename
        self.fh = open(filename, 'rb')

        self.st_size = os.stat(filename).st_size
        self.offset = 0

    def __del__(self):
        self.fh.close()

    def tell(self):
        return self.fh.tell()

    def seek(self, offset, whence=0):
        if whence == 0:
            self.offset = offset
        elif whence == 1:
            self.offset += offset
        elif whence == 2:
            self.offset = self.st_size - offset

        return self.fh.seek(offset, whence)

    def seekable(self):
        return True

    def read(self, amount):
        self.offset += amount
        result = self.fh.read(amount)
        return result

    # A slightly more accurate percentage
    def progress(self):
        return int(100.0 * self.offset / self.st_size)


class WebHandle(object):
    def __init__(self, url):
        self.url = url
        r = urlopen(url)
        if r.code != 200:
            raise FileNotFoundError(url)
        self.headers = self._headers_to_dict(r)
        if 'accept-ranges' not in self.headers:
            raise Exception("Site does not accept ranges")
        self.st_size = int(self.headers['content-length'])
        self.offset = 0

    def _headers_to_dict(self, r):
        result = {}
        if hasattr(r, 'getheaders'):
            for n, v in r.getheaders():
                result[n.lower()] = v.strip()
        else:
            for line in r.info().headers:
                if line.find(':') != -1:
                    n, v = line.split(': ', 1)
                    result[n.lower()] = v.strip()
        return result

    def tell(self):
        return self.offset

    def seek(self, offset, whence=0):
        if whence == 0:
            self.offset = offset
        elif whence == 1:
            self.offset += offset
        elif whence == 2:
            self.offset = self.st_size - offset
        return self.offset

    def seekable(self):
        return True

    def read(self, amount):
        start = self.offset
        end = self.offset + amount - 1
        req = Request(self.url,
                      headers={'Range': 'bytes=%d-%d' % (start, end)})
        r = urlopen(req)
        self.offset += amount
        result = r.read(amount)
        r.close()
        return result

    # A slightly more accurate percentage
    def progress(self):
        return int(100.0 * self.offset / self.st_size)


if __name__ == "__main__":
    exit(main())
