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

from pyVmomi import vim
import argparse
import getpass
from pyVim.connect import SmartConnectNoSSL, Disconnect
import atexit
import sys


def get_args():
    """Get command line args from the user.
    """
    parser = argparse.ArgumentParser(
        description='Standard Arguments for talking to vCenter')

    # because -h is reserved for 'help' we use -s for service
    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='vSphere service to connect to')

    # because we want -p for password, we use -o for port
    parser.add_argument('-o', '--port',
                        type=int,
                        default=443,
                        action='store',
                        help='Port to connect on')

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='User name to use when connecting to host')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to use when connecting to host')
    parser.add_argument('-vm','--vmname',
                        required=False,
                        action='store',
                        help='VM Name whose performance data needs to be retrieved')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password for host %s and user %s: ' %
                   (args.host, args.user))
    return args


def get_obj(content, vim_type, name):
    """

    :param content: content reference
    :param vim_type: vim object type
    :param name: Name whoes object needs to be returned
    :return: object of the type vim_type is returned
    """
    obj = None

    container = content.viewManager.CreateContainerView(content.rootFolder, vim_type, True)

    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def print_performace_metric(vm, perfManager,counterInfo):
    """
    :param vm: VM whoes performance metric needs to be printed
    :param perfManager: Performance Manager Managed Object Reference
    :param counterInfo: Metric CounterInfo
    :return: None
    """

    # Get all available metric IDs for this VM
    counterIDs = [m.counterId for m in
                  perfManager.QueryAvailablePerfMetric(entity=vm)]

    # Using the IDs form a list of MetricId
    # objects for building the Query Spec
    metricIDs = [vim.PerformanceManager.MetricId(counterId=c,
                                                 instance="*")
                 for c in counterIDs]

    # Build the specification to be used
    # for querying the performance manager
    spec = vim.PerformanceManager.QuerySpec(maxSample=1,
                                            entity=vm,
                                            metricId=metricIDs)
    # Query the performance manager
    # based on the metrics created above
    result = perfManager.QueryStats(querySpec=[spec])

    # Loop through the results and print the output
    output = ""
    for r in result:
        output += "name:        " + vm.summary.config.name + "\n"
        for val in result[0].value:
            # python3
            if sys.version_info[0] > 2:
                counterinfo_k_to_v = list(counterInfo.keys())[
                    list(counterInfo.values()).index(val.id.counterId)]
            # python2
            else:
                counterinfo_k_to_v = counterInfo.keys()[
                    counterInfo.values().index(val.id.counterId)]
            if val.id.instance == '':
                output += "%s: %s\n" % (
                    counterinfo_k_to_v, str(val.value[0]))
            else:
                output += "%s (%s): %s\n" % (
                    counterinfo_k_to_v, val.id.instance, str(val.value[0]))

    print(output)


def main():

    args = get_args()

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
        fullName = c.groupInfo.key + "." + c.nameInfo.key + "." + c.rollupType + "(" + c.unitInfo.key + ")"
        counterInfo[fullName] = c.key

    # create a list of vim.VirtualMachine objects so
    # that we can query them for statistics
    container = content.rootFolder
    viewType = [vim.VirtualMachine]
    recursive = True

    containerView = content.viewManager.CreateContainerView(container,
                                                            viewType,
                                                            recursive)
    children = containerView.view

    if args.vmname:
        vm = get_obj(content, [vim.VirtualMachine], args.vmname)
        print_performace_metric(vm, perfManager, counterInfo)

    else:
        # Loop through all the VMs
        for child in children:
            print_performace_metric(child, perfManager, counterInfo)


if __name__ == "__main__":
    main()
