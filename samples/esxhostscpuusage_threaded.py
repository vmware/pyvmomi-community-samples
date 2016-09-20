#!/usr/bin/python
""
Written by Gaurav Dogra
Github: https://github.com/dograga

Script to extract cpu usage of esxhosts on vcenter for last 1 hour with multithreading
""
import atexit
from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
import time
import datetime
from pyVmomi import vmodl
from threading import Thread

class perfdata():
   def metricvalue(self,item,depth):
      maxdepth=10
      if hasattr(item, 'childEntity'):
         if depth > maxdepth:
             return 0
         else:
             item = item.childEntity
             item=self.metricvalue(item,depth+1)
      return item

   def run(self,content,vihost):
       output=[]
       try:
          perf_dict = {}
          perfManager = content.perfManager
          perfList = content.perfManager.perfCounter
          for counter in perfList: #build the vcenter counters for the objects
              counter_full = "{}.{}.{}".format(counter.groupInfo.key,counter.nameInfo.key,counter.rollupType)
              perf_dict[counter_full] = counter.key
          counter_name = 'cpu.usage.average'
          counterId = perf_dict[counter_name]
          metricId = vim.PerformanceManager.MetricId(counterId=counterId, instance="")
          timenow=datetime.datetime.now()
          startTime = timenow - datetime.timedelta(hours=1)
          endTime = timenow
          search_index = content.searchIndex
          host = search_index.FindByDnsName(dnsName=vihost, vmSearch=False)
          query = vim.PerformanceManager.QuerySpec(entity=host,metricId=[metricId],intervalId=20,startTime=startTime,endTime=endTime)
          stats=perfManager.QueryPerf(querySpec=[query])
          count=0
          for val in stats[0].value[0].value:
              perfinfo={}
              val=float(val/100)
              perfinfo['timestamp']=stats[0].sampleInfo[count].timestamp
              perfinfo['hostname']=vihost
              perfinfo['value']=val
              output.append(perfinfo)
              count+=1
          for out in output:
	      print "Hostname: {}  TimeStame: {} Usage: {}".format (out['hostname'],out['timestamp'],out['value'])
       except vmodl.MethodFault as e:
           print("Caught vmodl fault : " + e.msg)
           return 0
       except Exception as e:
           print("Caught exception : " + str(e))
           return 0

def main():
   user='xxxxxxxx'
   passwd='xxxxxxxxx'
   port=443
   vc='xxxxxxxxxxxxxx'
   try:
       si = SmartConnect(
               host=vc,
               user=user,
               pwd=passwd,
               port=port)
   except:
       print "Failed to connect"
   atexit.register(Disconnect, si)
   content = si.RetrieveContent()
   perf=perfdata()
   for child in content.rootFolder.childEntity:
       datacenter=child
       hostfolder= datacenter.hostFolder
       hostlist=perf.metricvalue(hostfolder,0)
       for hosts in hostlist:
             esxhosts=hosts.host
             for esx in esxhosts:
                 summary=esx.summary
                 esxname=summary.config.name
                 p = Thread(target=perf.run, args=(content,esxname,))
                 p.start()

# start
if __name__ == "__main__":
    main()

