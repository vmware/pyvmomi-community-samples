#!/usr/bin/env python
# William Lam
# www.virtuallyghetto.com

"""
vSphere Python SDK program for demonstrating vSphere perfManager API based on
Rbvmomi sample https://gist.github.com/toobulkeh/6124975
"""

import datetime
from tools import cli, service_instance
from pyVmomi import vmodl, vim


def main():
    """
   Simple command-line program demonstrating vSphere perfManager API
   """

    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.VIHOST)
    args = parser.get_args()
    si = service_instance.connect(args)
    try:
        content = si.RetrieveContent()

        search_index = content.searchIndex
        # quick/dirty way to find an ESXi host
        host = search_index.FindByDnsName(dnsName=args.vihost, vmSearch=False)

        perf_manager = content.perfManager
        metric_id = vim.PerformanceManager.MetricId(counterId=6, instance="*")
        start_time = datetime.datetime.now() - datetime.timedelta(hours=1)
        end_time = datetime.datetime.now()

        query = vim.PerformanceManager.QuerySpec(maxSample=1,
                                                 entity=host,
                                                 metricId=[metric_id],
                                                 startTime=start_time,
                                                 endTime=end_time)

        print(perf_manager.QueryPerf(querySpec=[query]))

    except vmodl.MethodFault as ex:
        print("Caught vmodl fault : " + ex.msg)
        return -1
    except Exception as ex:
        print("Caught exception : " + str(ex))
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
