#!/usr/bin/python
# William Lam
# www.virtuallyghetto.com

"""
vSphere Python SDK program for listing Datastores in Datastore Cluster
"""

from optparse import OptionParser, make_option
from pyVim.connect import SmartConnect, Disconnect

from datetime import timedelta
from pyVmomi import vmodl
from pyVmomi import vim

import argparse
import atexit
import datetime
import sys


def GetArgs():
    """
   Supports the command-line arguments listed below.
   """
    parser = argparse.ArgumentParser(description='Process args for retrieving all the Virtual Machines')
    parser.add_argument('-s', '--host', required=True, action='store', help='Remote host to connect to')
    parser.add_argument('-o', '--port', type=int, default=443, action='store', help='Port to connect on')
    parser.add_argument('-u', '--user', required=True, action='store', help='User name to use when connecting to host')
    parser.add_argument('-p', '--password', required=True, action='store', help='Password to use when connecting to host')
    parser.add_argument('-d', '--dscluster', required=True, action='store', help='Name of vSphere Datastore Cluster')
    args = parser.parse_args()
    return args

def main():
    """
   Simple command-line program for listing Datastores in Datastore Cluster
   """

    args = GetArgs()
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
            print "Could not connect to the specified host using specified username and password"
            return -1

        atexit.register(Disconnect, si)

        content = si.RetrieveContent()
        # Search for all Datastore Clusters aka StoragePod
        objView = content.viewManager.CreateContainerView(content.rootFolder,[vim.StoragePod],True)
        datastoreClusters = objView.view
        objView.Destroy()
        
        for datastoreCluster in datastoreClusters:
            if datastoreCluster.name == args.dscluster:
                datastores = datastoreCluster.childEntity
                print "Datastores: "
                for datastore in datastores:
                    print datastore.name

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
