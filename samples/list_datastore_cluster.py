#!/usr/bin/env python
# William Lam
# www.virtuallyghetto.com

"""
vSphere Python SDK program for listing Datastores in Datastore Cluster
"""

from pyVmomi import vim
from pyVmomi import vmodl
from tools import cli, service_instance


def main():
    """
   Simple command-line program for listing Datastores in Datastore Cluster
   """

    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.DATASTORECLUSTER_NAME)
    args = parser.get_args()
    si = service_instance.connect(args)

    try:
        content = si.RetrieveContent()
        # Search for all Datastore Clusters aka StoragePod
        obj_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                           [vim.StoragePod],
                                                           True)
        ds_cluster_list = obj_view.view
        obj_view.Destroy()

        for ds_cluster in ds_cluster_list:
            if ds_cluster.name == args.datastorecluster_name:
                datastores = ds_cluster.childEntity
                print("Datastores: ")
                for datastore in datastores:
                    print(datastore.name)

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
