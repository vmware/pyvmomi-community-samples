#!/usr/bin/python
# -*- coding: utf-8 -*-

# VMware vSphere Python SDK
# Copyright (c) 2008-2014 VMware, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Written by Andre Pompas

Based on Gaurav Dogra code (https://github.com/dograga)

Script to extract Network usage (average) of ESXi hosts on vcenter
for last 1 hour with multithreading
"""

import atexit
import datetime

from pyVmomi import vmodl
from pyVmomi import vim
from pyVim.connect import SmartConnectNoSSL, Disconnect

from threading import Thread


class PerfData:
    def __init__(self):
        self.output = []

    def metric_value(self, item, depth):
        """
        Walk through depth of 'childEntity' and return ComputeResource
        """
        maxDepth = 10
        if hasattr(item, 'childEntity'):
            if depth > maxDepth:
                return 0
            else:
                item = item.childEntity
                item = self.metric_value(item, depth + 1)
        return item

    def run(self, content, vi_host):
        """
        Main function to query all wanted metrics
        """
        try:
            metrics = None
            perfDict = {}
            # Get all queryable aggregated and realtime metrics for an entity
            perfManager = content.perfManager
            # All listed metrics available
            perfList = content.perfManager.perfCounter
            # Build the vCenter counters for the objects
            for counter in perfList:
                counterFull = "{}.{}.{}".format(counter.groupInfo.key, counter.nameInfo.key, counter.rollupType)
                perfDict[counterFull] = counter.key

            # Set list of wanted metrics to query
            counterList = [
                'net.bytesRx.average',
                'net.bytesTx.average',
            ]

            for counterName in counterList:
                metrics = self.collect_metrics_for_entity(content, perfManager, perfDict, counterName, vi_host)
            if metrics is not None:
                for data in self.output:
                    print('Hostname: {}  TimeStamp: {}  Id: {}  Instance: {}  Counter: {}  Usage: {}'.format(
                        data['hostname'],
                        data['timestamp'],
                        data['id'],
                        data['instance'],
                        data['counter'],
                        data['value'])
                    )
                return 0
            else:
                print('Error: There is no metrics to query.')
                return 0

        except vmodl.MethodFault as e:
            print('Error: Caught vmodl fault -> ' + e.msg)
            return 0
        except Exception as e:
            print('Error: Caught exception -> ' + str(e))
            return 0

    def collect_metrics_for_entity(self, content, perf_manager, perf_dict, counter_name, vi_host):
        """
        Retrieves the performance metrics for the specified entity
        :param content: 
        :param perf_manager: 
        :param perf_dict: 
        :param counter_name: 
        :param vi_host: 
        :return: 
        """
        counterId = perf_dict[counter_name]
        metricId = vim.PerformanceManager.MetricId(counterId=counterId, instance="*")
        timeNow = datetime.datetime.now()
        # Query last 1 hour metrics
        startTime = timeNow - datetime.timedelta(seconds=3600)
        endTime = timeNow
        searchIndex = content.searchIndex
        host = searchIndex.FindByDnsName(dnsName=vi_host, vmSearch=False)
        query = vim.PerformanceManager.QuerySpec(
            entity=host,
            metricId=[metricId],
            intervalId=20,  # Minimum interval in seconds
            maxSample=5,  # Limits the number of samples returned
            startTime=startTime,
            endTime=endTime
        )
        stats = perf_manager.QueryPerf(querySpec=[query])
        metrics = stats[0] if len(stats) != 0 else None

        if metrics is not None:
            for metric in metrics.value:
                if metric.id.instance != "":
                    perfInfo = {}
                    instance = metric.id.instance
                    # Convert Kbp/s to bp/s
                    value = metric.value[0] * 1000 if instance.find('vmnic') != -1 else metric.value[0]
                    # value = float(value / 100)  # for CPU
                    perfInfo['timestamp'] = metrics.sampleInfo[0].timestamp
                    perfInfo['hostname'] = vi_host
                    perfInfo['instance'] = instance
                    perfInfo['id'] = metric.id.counterId
                    perfInfo['counter'] = counter_name
                    perfInfo['value'] = value
                    self.output.append(perfInfo)

        return metrics


def main():
    """
    Main function
    :return: 
    """
    user = 'username'
    passwd = 'password'
    port = 443
    vc = 'hostname'
    si = None

    try:
        si = SmartConnectNoSSL(
            host=vc,
            user=user,
            pwd=passwd,
            port=port)
    except Exception as e:
        print('Error: Failed to connect : ' + str(e))

    # Disconnect from ESXi host
    atexit.register(Disconnect, si)
    # Retrieve content of ESXI host
    content = si.RetrieveContent()
    # Init our class
    perf = PerfData()
    for child in content.rootFolder.childEntity:
        datacenter = child
        hostFolder = datacenter.hostFolder
        hostList = perf.metric_value(hostFolder, 0)
        for hosts in hostList:
            esxiHosts = hosts.host
            for esx in esxiHosts:
                summary = esx.summary
                esxiName = summary.config.name
                p = Thread(target=perf.run, args=(content, esxiName))
                p.start()


# start
if __name__ == "__main__":
    main()
