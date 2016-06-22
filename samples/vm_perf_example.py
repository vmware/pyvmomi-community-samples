#!/usr/bin/env python
"""
 Written by Lance Hasson
 Github: https://github.com/JLHasson

 Script to report all available realtime performance metrics from a virtual machine.
 Based on a Java example available in the VIM API 6.0 documentationavailable online at:
 https://pubs.vmware.com/vsphere-60/index.jsp?topic=%2Fcom.vmware.wssdk.pg.doc%2FPG_Performance.18.4.html&path=7_1_0_1_15_2_4
"""

from pyVmomi import vim
from tools import cli
from pyVim.connect import SmartConnectNoSSL, Disconnect
import atexit,getpass
    
def main():

    args = cli.get_args()
    
    # Connect to the host without SSL signing
    try: 
        si = SmartConnectNoSSL(
            host=args.host,
            user=args.user,
            pwd=args.password,
            port=int(args.port))
        atexit.register(Disconnect, si)

    except IOError as e:
        pass

    if not si:
        raise SystemExit("Unable to connect to host with supplied info.")


    content = si.RetrieveContent()
    perfManager = content.perfManager

    # create a mapping from performance stats to their counterIDs
    # counterInfo: [performance stat => counterId]
    # performance stat example: cpu.usagemhz.LATEST
    # counterId example: 6
    counterInfo = {}
    for c in perfManager.perfCounter:
        prefix = c.groupInfo.key
        fullName = c.groupInfo.key + "." + c.nameInfo.key + "." + c.rollupType
        counterInfo[fullName] = c.key

    # create a list of vim.VirtualMachine objects so that we can query them for statistics
    container = content.rootFolder #where to start looking
    viewType = [vim.VirtualMachine] #what object type to look for
    recursive = True #whether to run recursive search or not

    containerView = content.viewManager.CreateContainerView(container, viewType, recursive)
    children = containerView.view

    # Loop through all the VMs
    for child in children:
        # Get all available metric IDs for this VM
        counterIDs = [m.counterId for m in perfManager.QueryAvailablePerfMetric(entity=child)]

        # Using the IDs form a list of MetricId objects for building the Query Spec
        metricIDs = [vim.PerformanceManager.MetricId(counterId=c, instance="*") for c in counterIDs]
        
        # Build the specification to be used for querying the performance manager
        spec = vim.PerformanceManager.QuerySpec(maxSample=1,
                                                entity=child,
                                                metricId=metricIDs) #must be passed as list
        # Query the performance manager based on the metrics created above
        result = perfManager.QueryStats(querySpec=[spec]) #must pass as list

        # Loop through the results and print the output
        output = ""
        for r in result:
            output += "name:        " + child.summary.config.name + "\n"
            for val in result[0].value:
                output += counterInfo.keys()[counterInfo.values().index(val.id.counterId)] + ": " + str(val.value[0]) + "\n"
            output += "\n"

        print(output)

if __name__ == "__main__":
    main()