#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2022-2024 Broadcom. All Rights Reserved.
The term "Broadcom" refers to Broadcom Inc. and/or its subsidiaries.

This file includes sample code for IO trip analyzer schedules configuration.

To provide an example of IO trip analyzer recurrence configuration, it shows how
to get a cluster's IO trip analyzer scheduler configuration, and how to create,
edit or delete an IO trip analyzer scheduler recurrence.

"""

__author__ = 'Broadcom, Inc'

import argparse
import atexit
import time
import datetime
import getpass
import ssl
import sys
import vsanapiutils
from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect


TIME_STRING_FORMAT = 'YYYY-MM-DD HH:MM'
TIME_FORMAT = '%Y-%m-%d %H:%M'


def validTime(timeStr):
   try:
      timestamp = time.mktime(time.strptime(timeStr, TIME_FORMAT))
      return datetime.datetime.utcfromtimestamp(timestamp)
   except ValueError:
      msg = "not a valid time: " + timeStr
      raise argparse.ArgumentTypeError(msg)


def addArgumentsOfRecurrence(parser, isCreate):
   # name
   parser.add_argument(
      '--name', required=not isCreate, action='store', metavar='recurrenceName',
      help="The unique name for this recurrence setting.")
   # target vm
   parser.add_argument(
      '--vm', dest='vmName', metavar='VM', required=isCreate,
      help='Name of the target virtual machine to run IO trip analyzer'
           ' diagnostics.')
   # startTime
   parser.add_argument(
      '--startTime', required=isCreate, action='store', type=validTime,
      help='The start time for the recurrence. Format: %s' % TIME_STRING_FORMAT)
   # endTime
   parser.add_argument(
      '--endTime', required=False, action='store', type=validTime,
      help='The end time for the recurrence. If not set, the recurrence will'
      ' not end. Format: %s' % TIME_STRING_FORMAT)
   # duration
   parser.add_argument(
      '--duration', required=isCreate, type=int, action='store',
      help='The diagnostic duration for each IO trip analyzer occurence. The'
           ' unit is second.')
   # interval
   parser.add_argument(
      '--interval', required=isCreate, type=int, action='store',
      help='The time interval between two IO trip analyzer tasks. If the value'
           ' is set to 0, it means it is a one-time scheduling. Unit is second.')
   # status
   parser.add_argument(
      '--status', required=False, action='store',
      choices=[vim.vsan.VsanIOTripAnalyzerRecurrenceStatus.recurrenceEnabled,
               vim.vsan.VsanIOTripAnalyzerRecurrenceStatus.recurrenceDisabled],
      help='The recurrence status.')


def getArgs():
   """
    Supports the command-line arguments listed below.
   """
   commonArgsParser = argparse.ArgumentParser(
      description='Args for connecting to vCenter server and the cluster',
      add_help=False)
   commonArgsParser.add_argument('-s', '--vc', required=True, action='store',
                                 help='Remote vCenter Server to connect to')
   commonArgsParser.add_argument('-o', '--port', type=int, default=443, action='store',
                                 help='Port to connect on')
   commonArgsParser.add_argument('-u', '--user', required=True, action='store',
                                 help='User name to use when connecting to vCenter Server')
   commonArgsParser.add_argument('-p', '--password', required=False, action='store',
                                 help='Password to use when connecting to vCenter Server')
   commonArgsParser.add_argument('--cluster', dest='clusterName', metavar="CLUSTER",
                                 default='VSAN-Cluster')

   parser = argparse.ArgumentParser(
      description='Process args for vSAN SDK sample application')
   subParsers = parser.add_subparsers(dest='action', title='subcommands')

   # arguments for creating an recurrence
   parserCreateRecur = subParsers.add_parser(
      'create', help='create an IO trip analyzer recurrence',
      parents=[commonArgsParser])
   addArgumentsOfRecurrence(parserCreateRecur, isCreate=True)

   # arguments for editing an recurrence
   parserEditRecur = subParsers.add_parser(
      'edit', help='edit an existing IO trip analyzer recurrence',
      parents=[commonArgsParser])
   addArgumentsOfRecurrence(parserEditRecur, isCreate=False)

   # arguments for removing an recurrence
   parserRemoveRecur = subParsers.add_parser(
      'remove', help='remove an existing IO trip analyzer recurrence',
      parents=[commonArgsParser])
   parserRemoveRecur.add_argument(
      '--name', required=True, action='store', metavar='recurrenceName',
      help="Name of the recurrence to be removed")

   # arguments for getting cluster's recurrences
   parserGetRecur = subParsers.add_parser(
      'get', help="get the cluster's IO trip analyzer recurrences",
      parents=[commonArgsParser])

   args = parser.parse_args()
   return args


def connectToServers(args):
   """
   """
   if args.password:
      password = args.password
   else:
      password = getpass.getpass(prompt='Enter password for vc %s and '
                                        'user %s: ' % (args.vc, args.user))

   # For python 2.7.9 and later, the default SSL context has stricter
   # connection handshaking rule, hence we are turning off the hostname checking
   # and client side cert verification.
   sslContext = None
   if sys.version_info[:3] > (2, 7, 8):
      sslContext = ssl.create_default_context()
      sslContext.check_hostname = False
      sslContext.verify_mode = ssl.CERT_NONE

   # Connect to vCenter, get vc service instance
   si = SmartConnect(host=args.vc,
                     user=args.user,
                     pwd=password,
                     port=int(args.port),
                     sslContext=sslContext)
   atexit.register(Disconnect, si)

   aboutInfo = si.content.about
   if aboutInfo.apiType != 'VirtualCenter':
      raise Exception("The sample script should be run against vc.")

   # Get vSAN diagnostics system from the vCenter Managed Object references.
   apiVersion = vsanapiutils.GetLatestVmodlVersion(args.vc, int(args.port))
   vsanVcMos = vsanapiutils.GetVsanVcMos(si._stub,
                                         context=sslContext,
                                         version=apiVersion)
   cds = vsanVcMos['vsan-cluster-diagnostics-system']

   return (si, cds)


def getClusterOrVMInstance(content, entityName, isCluster):
   searchIndex = content.searchIndex
   datacenters = content.rootFolder.childEntity
   for datacenter in datacenters:
      if isCluster:
         folder = datacenter.hostFolder
      else:
         folder = datacenter.vmFolder
      instance = getManagedEntityInstance(searchIndex, folder, entityName)
      if instance is not None:
         return instance
   return None


def getManagedEntityInstance(searchIndex, folder, entityName):
   # searches the immediate children of folder
   instance = searchIndex.FindChild(folder, entityName)
   if instance is not None:
      return instance
   # searches the child folders
   for child in folder.childEntity:
      if isinstance(child, vim.Folder):
         instance = getManagedEntityInstance(searchIndex, child, entityName)
         if instance is not None:
            return instance
   return None


def createRecurrence(content, cds, cluster, args):
   vm = getClusterOrVMInstance(content, args.vmName, isCluster=False)
   if vm is None:
      raise Exception("VM %s is not found for %s" % (args.vmName, args.vc))
   target = vim.vsan.IODiagnosticsTarget(
      type=vim.vsan.IODiagnosticsTargetType.VirtualMachine,
      entityId=vm._moId)
   if args.status is None:
      args.status = \
         vim.vsan.VsanIOTripAnalyzerRecurrenceStatus.recurrenceEnabled
   # note: startTime and endTime should be a utc datetime
   spec = vim.vsan.VsanIOTripAnalyzerRecurrence(name=args.name,
                                                targets=[target],
                                                startTime=args.startTime,
                                                endTime=args.endTime,
                                                duration=args.duration,
                                                interval=args.interval,
                                                status=args.status)
   recurs = cds.CreateIOTripAnalyzerRecurrences(cluster, recurrences=[spec])
   print("Recurrence %s has been created sucessfully!" % recurs[0].name)
   print("The detail of the recurrence is: %s" % recurs[0])


def editRecurrence(content, cds, cluster, args):
   existingSpec = None
   config = cds.GetIOTripAnalyzerSchedulerConfig(cluster)
   for recurrence in config.recurrences:
      if recurrence.name == args.name:
         existingSpec = recurrence
         break
   if existingSpec is None:
      raise Exception("Recurrence %s does not exist" % args.name)
   # get vm instance
   target = None
   if args.vmName:
     vm = getClusterOrVMInstance(content, args.vmName, isCluster=False)
     if vm is None:
        raise Exception("VM %s is not found for %s" % (args.vmName, args.vc))
     target = vim.vsan.IODiagnosticsTarget(
        type=vim.vsan.IODiagnosticsTargetType.VirtualMachine,
        entityId=vm._moId)
   spec = vim.vsan.VsanIOTripAnalyzerRecurrence(
      name=existingSpec.name,
      targets=[target] if target is not None else existingSpec.targets,
      startTime=args.startTime if args.startTime else existingSpec.startTime,
      endTime=args.endTime if args.endTime else existingSpec.endTime,
      duration=args.duration if args.duration else existingSpec.duration,
      interval=args.interval if args.interval else existingSpec.interval,
      status=args.status if args.status else existingSpec.status)
   recurs = cds.EditIOTripAnalyzerRecurrences(cluster, recurrences=[spec])
   print("Recurrence %s has been updated successfully!" % args.name)
   print("The detail of the recurrence is: %s" % recurs[0])


def main():
   args = getArgs()
   (si, cds) = connectToServers(args)

   # get cluster instance
   content = si.RetrieveContent()
   cluster = getClusterOrVMInstance(content, args.clusterName, isCluster=True)
   if cluster is None:
      print("Cluster %s is not found for %s" % (args.clusterName, args.vc))
      return -1

   if args.action == 'create':
      createRecurrence(content, cds, cluster, args)
   elif args.action == 'edit':
      editRecurrence(content, cds, cluster, args)
   elif args.action == 'remove':
      cds.RemoveIOTripAnalyzerRecurrences(cluster, names=[args.name])
      print("Recurrence %s has been removed successfully!" % args.name)
   else:
      config = cds.GetIOTripAnalyzerSchedulerConfig(cluster)
      print("Recurences of cluster %s:" % (args.clusterName))
      print(config.recurrences)


if __name__ == '__main__':
   main()
