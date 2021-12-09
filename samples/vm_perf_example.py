#!/usr/bin/env python
"""
 Written by Lance Hasson
 Github: https://github.com/JLHasson

 Script to report all available realtime performance metrics from a
 virtual machine. Based on a Java example available in the VIM API 6.0
 documentationavailable online at:
 https://pubs.vmware.com/vsphere-60/index.jsp?topic=%2Fcom.vmware.wssdk.pg.
 doc%2FPG_Performance.18.4.html&path=7_1_0_1_15_2_4

 Requirements:
     VM tools must be installed on all virtual machines.
"""

import sys
from pyVmomi import vim
from tools import cli, service_instance


def main():

    parser = cli.Parser()
    args = parser.get_args()
    si = service_instance.connect(args)

    content = si.RetrieveContent()
    perf_manager = content.perfManager

    # create a mapping from performance stats to their counterIDs
    # counterInfo: [performance stat => counterId]
    # performance stat example: cpu.usagemhz.LATEST
    # counterId example: 6
    counter_info = {}
    for counter in perf_manager.perfCounter:
        full_name = counter.groupInfo.key + "." + \
                    counter.nameInfo.key + "." + counter.rollupType
        counter_info[full_name] = counter.key

    # create a list of vim.VirtualMachine objects so
    # that we can query them for statistics
    container = content.rootFolder
    view_type = [vim.VirtualMachine]
    recursive = True

    container_view = content.viewManager.CreateContainerView(container, view_type, recursive)
    children = container_view.view

    # Loop through all the VMs
    for child in children:
        # Get all available metric IDs for this VM
        counter_ids = [m.counterId for m in perf_manager.QueryAvailablePerfMetric(entity=child)]

        # Using the IDs form a list of MetricId
        # objects for building the Query Spec
        metric_ids = [vim.PerformanceManager.MetricId(
            counterId=counter, instance="*") for counter in counter_ids]

        # Build the specification to be used
        # for querying the performance manager
        spec = vim.PerformanceManager.QuerySpec(maxSample=1,
                                                entity=child,
                                                metricId=metric_ids)
        # Query the performance manager
        # based on the metrics created above
        result_stats = perf_manager.QueryStats(querySpec=[spec])

        # Loop through the results and print the output
        output = ""
        for _ in result_stats:
            output += "name:        " + child.summary.config.name + "\n"
            for val in result_stats[0].value:
                # python3
                if sys.version_info[0] > 2:
                    counterinfo_k_to_v = list(counter_info.keys())[
                        list(counter_info.values()).index(val.id.counterId)]
                # python2
                else:
                    counterinfo_k_to_v = counter_info.keys()[
                        counter_info.values().index(val.id.counterId)]
                if val.id.instance == '':
                    output += "%s: %s\n" % (
                        counterinfo_k_to_v, str(val.value[0]))
                else:
                    output += "%s (%s): %s\n" % (
                        counterinfo_k_to_v, val.id.instance, str(val.value[0]))

        print(output)


if __name__ == "__main__":
    main()
