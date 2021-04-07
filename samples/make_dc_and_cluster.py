#!/usr/bin/env python
"""
Written by Michael Rice
Github: https://github.com/michaelrice
Website: https://michaelrice.github.io/
Blog: http://www.errr-online.com/
This code has been released under the terms of the Apache 2.0 license
http://opensource.org/licenses/Apache-2.0
"""

from tools import cluster, service_instance, datacenter, cli, pchelper
from pyVmomi import vim


parser = cli.Parser()
parser.add_required_arguments(cli.Argument.DATACENTER_NAME, cli.Argument.CLUSTER_NAME)
args = parser.get_args()
si = service_instance.connect(args)

content = si.RetrieveContent()
if pchelper.search_for_obj(content, [vim.Datacenter], args.datacenter_name):
    print("Datacenter '%s' already exists" % args.datacenter_name)
else:
    dc = datacenter.create_datacenter(dc_name=args.datacenter_name, service_instance=si)
    cluster.create_cluster(datacenter=dc, name=args.cluster_name)
    print("created DC and cluster")
