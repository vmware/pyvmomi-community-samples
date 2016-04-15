#!/usr/bin/env python
"""
 Written by Tony Allen
 Github: https://github.com/stormbeard
 Blog: https://stormbeard.net/
 This code has been released under the terms of the Apache 2 licenses
 http://www.apache.org/licenses/LICENSE-2.0.html

 Script to deploy VM via a single .ovf and a single .vmdk file.
"""
import ssl
from sys import exit
from argparse import ArgumentParser
from getpass import getpass

from pyVim import connect


def get_args():
    """
    Get CLI arguments.
    """
    parser = ArgumentParser(description='Arguments for talking to vCenter')

    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='vSphere service to connect to.')

    parser.add_argument('-o', '--port',
                        type=int,
                        default=443,
                        action='store',
                        help='Port to connect on.')

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='Username to use.')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to use.')

    parser.add_argument('--datacenter_name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the Datacenter you\
                          wish to use. If omitted, the first\
                          datacenter will be used.')

    parser.add_argument('--cluster_name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the cluster you wish the VM to\
                          end up on. If left blank the first cluster found\
                          will be used')

    parser.add_argument('--host_name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the host you wish the VM to\
                          end up on. If left blank the first cluster found\
                          will be used')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass(prompt='Enter password: ')

    return args


def get_obj_in_list(obj_name, obj_list):
    """
    Gets an object out of a list (obj_list) whos name matches obj_name.
    """
    for o in obj_list:
        if o.name == obj_name:
            return o
    print ("Unable to find object by the name of %s in list:\n%s" %
           (o.name, map(lambda o: o.name, obj_list)))
    exit(1)


def get_objects(si, args):
    """
    Return a dict containing the necessary objects for deployment.
    """
    # Get datacenter object.
    datacenter_list = si.content.rootFolder.childEntity
    if args.datacenter_name:
        datacenter_obj = get_obj_in_list(args.datacenter_name, datacenter_list)
    else:
        datacenter_obj = datacenter_list[0]

    # Get cluster object.
    cluster_list = datacenter_obj.hostFolder.childEntity
    if args.cluster_name:
        cluster_obj = get_obj_in_list(args.cluster_name, cluster_list)
    elif len(cluster_list) > 0:
        cluster_obj = cluster_list[0]
    else:
        print "No clusters found in DC (%s)." % datacenter_obj.name

    # Get host object.
    host_list = cluster_obj.host
    if args.host_name:
        host_obj = get_obj_in_list(args.host_name, host_list)
    elif len(cluster_list) > 0:
        host_obj = host_list[0]
    else:
        print "No host found in Cluster (%s)." % cluster_obj.name

    return {"datacenter": datacenter_obj,
            "host": host_obj}


def wait_for_task(task):
    """ wait for a vCenter task to finish """
    task_done = False
    while not task_done:
        if task.info.state == 'success':
            return task.info.result

        if task.info.state == 'error':
            print "there was an error"
            task_done = True


def main():
    args = get_args()
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        si = connect.SmartConnect(host=args.host,
                                  user=args.user,
                                  pwd=args.password,
                                  port=args.port,
                                  sslContext=ctx)
    except:
        print "Unable to connect to %s" % args.host
        exit(1)
    objs = get_objects(si, args)
    enableSSH(objs["host"])
    disableSSH(objs["host"])

    connect.Disconnect(si)


def enableSSH(host):
    for service in host.configManager.serviceSystem.serviceInfo.service:
        print "key: %s" % service.key
        print "label: %s" % service.label
        print "policy: %s" % service.policy
        print "running: %s" % service.running
        print "========================"
        print

    host.configManager.serviceSystem.Start("TSM-SSH")


def disableSSH(host):
    for service in host.configManager.serviceSystem.serviceInfo.service:
        print "key: %s" % service.key
        print "label: %s" % service.label
        print "policy: %s" % service.policy
        print "running: %s" % service.running
        print "========================"
        print

    host.configManager.serviceSystem.Stop("TSM-SSH")

if __name__ == "__main__":
    exit(main())
