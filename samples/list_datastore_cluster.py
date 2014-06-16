#!/usr/bin/env python
# William Lam
# www.virtuallyghetto.com

"""
vSphere Python SDK program for listing Datastores in Datastore Cluster
"""
import argparse
import atexit

from pyVmomi import vim
from pyVmomi import vmodl
from pyVim import connect


def get_args():
    """
   Supports the command-line arguments listed below.
   """
    parser = argparse.ArgumentParser(
        description='Process args for retrieving all the Virtual Machines')

    parser.add_argument('-s', '--host',
                        required=True, action='store',
                        help='Remote host to connect to')

    parser.add_argument('-o', '--port',
                        type=int, default=443,
                        action='store', help='Port to connect on')

    parser.add_argument('-u', '--user', required=True,
                        action='store',
                        help='User name to use when connecting to host')

    parser.add_argument('-p', '--password',
                        required=True, action='store',
                        help='Password to use when connecting to host')

    parser.add_argument('-d', '--dscluster', required=True, action='store',
                        help='Name of vSphere Datastore Cluster')

    args = parser.parse_args()
    return args


def main():
    """
   Simple command-line program for listing Datastores in Datastore Cluster
   """

    args = get_args()

    try:
        service_instance = connect.SmartConnect(host=args.host,
                                                user=args.user,
                                                pwd=args.password,
                                                port=int(args.port))
        if not service_instance:
            print("Could not connect to the specified host using "
                  "specified username and password")
            return -1

        atexit.register(connect.Disconnect, service_instance)

        content = service_instance.RetrieveContent()
        # Search for all Datastore Clusters aka StoragePod
        obj_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                           [vim.StoragePod],
                                                           True)
        ds_cluster_list = obj_view.view
        obj_view.Destroy()

        for ds_cluster in ds_cluster_list:
            if ds_cluster.name == args.dscluster:
                datastores = ds_cluster.childEntity
                print "Datastores: "
                for datastore in datastores:
                    print datastore.name

    except vmodl.MethodFault as error:
        print "Caught vmodl fault : " + error.msg
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
