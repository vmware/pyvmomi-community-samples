"""
Written by Michael Rice
Github: https://github.com/michaelrice
Website: https://michaelrice.github.io/
Blog: http://www.errr-online.com/
This code has been released under the terms of the Apache-2.0 license
http://opensource.org/licenses/Apache-2.0

Example to show the minimal steps required to create a cluster in
vCenter.

Required Privileges
Host.Inventory.CreateCluster

Since
VI API 2.5
"""
from pyVmomi import vim


def create_cluster(**kwargs):
    """
    Method to create a Cluster in vCenter

    :param kwargs:
    :return: Cluster MORef
    """
    cluster_name = kwargs.get("name")
    cluster_spec = kwargs.get("cluster_spec")
    datacenter = kwargs.get("datacenter")

    if cluster_name is None:
        raise ValueError("Missing value for name.")
    if datacenter is None:
        raise ValueError("Missing value for datacenter.")
    if cluster_spec is None:
        cluster_spec = vim.cluster.ConfigSpecEx()

    host_folder = datacenter.hostFolder
    cluster = host_folder.CreateClusterEx(name=cluster_name, spec=cluster_spec)
    return cluster
