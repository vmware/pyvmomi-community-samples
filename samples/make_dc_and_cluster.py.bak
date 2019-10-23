#!/usr/bin/env python
"""
Written by Michael Rice
Github: https://github.com/michaelrice
Website: https://michaelrice.github.io/
Blog: http://www.errr-online.com/
This code has been released under the terms of the Apache 2.0 license
http://opensource.org/licenses/Apache-2.0
"""
import atexit

from pyVim.connect import SmartConnect, Disconnect

from tools import cluster
from tools import datacenter
from tools import cli


PARSER = cli.build_arg_parser()
PARSER.add_argument("-n", "--dcname",
                    required=True,
                    action="store",
                    help="Name of the Datacenter to create.")

PARSER.add_argument("-c", "--cname",
                    required=True,
                    action="store",
                    help="Name to give the cluster to be created.")

MY_ARGS = PARSER.parse_args()
cli.prompt_for_password(MY_ARGS)
SI = SmartConnect(host=MY_ARGS.host,
                  user=MY_ARGS.user,
                  pwd=MY_ARGS.password,
                  port=MY_ARGS.port)

atexit.register(Disconnect, SI)
dc = datacenter.create_datacenter(dcname=MY_ARGS.dcname, service_instance=SI)
cluster.create_cluster(datacenter=dc, name=MY_ARGS.cname)
