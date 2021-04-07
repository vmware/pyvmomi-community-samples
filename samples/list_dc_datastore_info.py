#!/usr/bin/env python
#
# Written by JM Lopez
# GitHub: https://github.com/jm66
# Email: jm@jmll.me
# Website: http://jose-manuel.me
#
# Note: Example code For testing purposes only
#
# This code has been released under the terms of the Apache-2.0 license
# http://opensource.org/licenses/Apache-2.0
#

import requests
from pyVmomi import vim
from tools import cli, service_instance, pchelper

# disable  urllib3 warnings
requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning)


# http://stackoverflow.com/questions/1094841/
def sizeof_fmt(num):
    """
    Returns the human readable version of a file size

    :param num:
    :return:
    """
    for item in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, item)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')


def print_datastore_info(ds_obj):
    summary = ds_obj.summary
    ds_capacity = summary.capacity
    ds_freespace = summary.freeSpace
    ds_uncommitted = summary.uncommitted if summary.uncommitted else 0
    ds_provisioned = ds_capacity - ds_freespace + ds_uncommitted
    ds_overp = ds_provisioned - ds_capacity
    ds_overp_pct = (ds_overp * 100) / ds_capacity \
        if ds_capacity else 0
    print("")
    print("Name                  : {}".format(summary.name))
    print("URL                   : {}".format(summary.url))
    print("Capacity              : {} GB".format(sizeof_fmt(ds_capacity)))
    print("Free Space            : {} GB".format(sizeof_fmt(ds_freespace)))
    print("Uncommitted           : {} GB".format(sizeof_fmt(ds_uncommitted)))
    print("Provisioned           : {} GB".format(sizeof_fmt(ds_provisioned)))
    if ds_overp > 0:
        print("Over-provisioned      : {} GB / {} %".format(
            sizeof_fmt(ds_overp),
            ds_overp_pct))
    print("Hosts                 : {}".format(len(ds_obj.host)))
    print("Virtual Machines      : {}".format(len(ds_obj.vm)))


def main():
    parser = cli.Parser()
    parser.add_optional_arguments(cli.Argument.DATASTORE_NAME)
    args = parser.get_args()
    si = service_instance.connect(args)

    content = si.RetrieveContent()
    # Get list of ds mo
    datastore = pchelper.search_for_obj(content, [vim.Datastore], args.datastore_name)
    if datastore:
        ds_obj_list = [datastore]
    else:
        ds_obj_list = pchelper.get_all_obj(content, [vim.Datastore])

    for ds in ds_obj_list:
        print_datastore_info(ds)


# start
if __name__ == "__main__":
    main()
