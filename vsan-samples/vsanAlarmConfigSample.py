#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2023-2024 Broadcom. All Rights Reserved.
The term "Broadcom" refers to Broadcom Inc. and/or its subsidiaries.

Starting with 8.0 Update 3, we offer users the capability to configure
SSD endurance alarms for vSAN ESA clusters.

It provides the example of simplifing the process of setting up alarms
by allowing users to configure alarms through the vSAN SDK, eliminating
the need to add alarm rules individually.

"""

__author__ = 'Broadcom, Inc'

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, VmomiSupport
import sys
import ssl
import atexit
import argparse
import getpass
if sys.version[0] < '3':
   input = raw_input

# Import the vSAN API python bindings and utilities.
import pyVmomi
import vsanmgmtObjects
import vsanapiutils

TARGET_ALARM = 'alarm.esx.problem.vsan.health.ssd.endurance'

def GetArgs():
   """
   Supports the command-line arguments listed below.
   """
   parser = argparse.ArgumentParser(
       description='Process args for vSAN SDK sample application')
   parser.add_argument('-s', '--host', required=True, action='store',
                       help='Remote host to connect to')
   parser.add_argument('-o', '--port', type=int, default=443, action='store',
                       help='Port to connect on')
   parser.add_argument('-u', '--user', required=True, action='store',
                       help='User name to use when connecting to host')
   parser.add_argument('-p', '--password', required=False, action='store',
                       help='Password to use when connecting to host')
   args = parser.parse_args()
   return args

def main():
   args = GetArgs()
   if args.password:
      password = args.password
   else:
      password = getpass.getpass(prompt='Enter password for host %s and '
                                        'user %s: ' % (args.host,args.user))

   # For python 2.7.9 and later, the default SSL context has more strict
   # connection handshaking rule. We may need turn off the hostname checking
   # and client side cert verification.
   context = None
   if sys.version_info[:3] > (2,7,8):
      context = ssl.create_default_context()
      context.check_hostname = False
      context.verify_mode = ssl.CERT_NONE

   si = SmartConnect(host=args.host,
                     user=args.user,
                     pwd=password,
                     port=int(args.port),
                     sslContext=context)

   atexit.register(Disconnect, si)

   # Detecting whether the host is vCenter or ESXi.
   aboutInfo = si.content.about
   apiVersion = vsanapiutils.GetLatestVmodlVersion(args.host, int(args.port))
   if aboutInfo.apiType != 'VirtualCenter':
      print("The type of target is not vCenter...")
      return -1

   alarmManager = si.content.alarmManager
   alarms = alarmManager.GetAlarm(si.content.rootFolder)
   targetAlarm = None
   for alarm in alarms:
      if alarm.info.systemName == TARGET_ALARM:
         targetAlarm = alarm
         break
   if not targetAlarm:
      print('Alarm: %s is not found' % TARGET_ALARM)
      return -1

   expressions = []
   # Alarm rule for cluster name not found
   expressions.append(
      vim.alarm.EventAlarmExpression(
         eventType = vim.event.EventEx,
         eventTypeId = 'vsan.health.test.ssdendurance.clusternotfound.event',
         objectType = vim.HostSystem,
         comparisons = [],
         status = 'yellow'
      )
   )

   # Alarm rules for disk percentage threshold configuration
   comparisons = [
      vim.EventAlarmExpressionComparison(
         attributeName = 'Disk Percentage Threshold',
         value = '95',
         operator = 'equals',
      ), vim.EventAlarmExpressionComparison(
         attributeName = 'Cluster Name',
         # Update cluster name here to existing cluster name in the inventory
         value = 'vSAN-ESA-Cluster',
         operator = 'equals',
      ), vim.EventAlarmExpressionComparison(
         attributeName = 'host.name',
         # Update host name here to existing cluster name in the inventory
         value = '10.1.2.3',
         operator = 'equals',
      ), vim.EventAlarmExpressionComparison(
         attributeName = 'Disk Name',
         # Update disk and operator name here according to target host
         value = 't10.NVMe',
         operator = 'startsWith',
      )
   ]

   expressions.append(
      vim.alarm.EventAlarmExpression(
         eventType = vim.event.EventEx,
         eventTypeId = 'esx.problem.vsan.health.ssd.endurance',
         objectType = vim.HostSystem,
         comparisons = comparisons,
         status = 'red'
      )
   )

   # Reconfigure alarm
   info = targetAlarm.info
   spec = vim.alarm.AlarmSpec(
      action=info.action,
      name=info.name,
      systemName=info.systemName,
      actionFrequency = info.actionFrequency,
      description=info.description,
      enabled=info.enabled,
      expression=vim.alarm.OrAlarmExpression(expression=expressions),
      setting=info.setting,
   )
   targetAlarm.ReconfigureAlarm(spec)

   print('Alarm reconfiguration is completed')

if __name__ == "__main__":
   main()
