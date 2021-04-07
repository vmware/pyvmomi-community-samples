#!/usr/bin/env python
# William Lam
# www.virtuallyghetto.com

"""
vSphere Python SDK program for demonstrating vSphere perfManager API based on
Rbvmomi sample https://gist.github.com/toobulkeh/6124975
"""

import datetime
from tools import cli, service_instance
from pyVmomi import vmodl
from pyVmomi import vim


def main():
    """
   Simple command-line program demonstrating vSphere perfManager API
   """

    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.VIHOST)
    args = parser.get_args()
    serviceInstance = service_instance.connect(args)
    try:
        content = serviceInstance.RetrieveContent()

        search_index = content.searchIndex
        # quick/dirty way to find an ESXi host
        host = search_index.FindByDnsName(dnsName=args.vihost, vmSearch=False)

        perfManager = content.perfManager
        metricId = vim.PerformanceManager.MetricId(counterId=6, instance="*")
        startTime = datetime.datetime.now() - datetime.timedelta(hours=1)
        endTime = datetime.datetime.now()

        query = vim.PerformanceManager.QuerySpec(maxSample=1,
                                                 entity=host,
                                                 metricId=[metricId],
                                                 startTime=startTime,
                                                 endTime=endTime)

        print(perfManager.QueryPerf(querySpec=[query]))

    except vmodl.MethodFault as e:
        print("Caught vmodl fault : " + e.msg)
        return -1
    except Exception as e:
        print("Caught exception : " + str(e))
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
