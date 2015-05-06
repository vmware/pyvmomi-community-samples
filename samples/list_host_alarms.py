#!/usr/bin/env python
"""
Written by Michael Rice
Github: https://github.com/michaelrice
Website: https://michaelrice.github.io/
Blog: http://www.errr-online.com/
This code has been released under the terms of the Apache-2.0 license
http://opensource.org/licenses/Apache-2.0
"""
from __future__ import print_function

import atexit

from pyVim.connect import SmartConnect, Disconnect

from tools import alarm
from tools import cli


PARSER = cli.build_arg_parser()
# If you are unsure where to get the UUID of your HostSystem check out the
# MOB. For example in my lab I would connect directly to the host mob like so:
# https://10.12.254.10/mob/?moid=ha-host&doPath=hardware%2esystemInfo
PARSER.add_argument("-x", "--uuid",
                    required=True,
                    action="store",
                    help="The UUID of the HostSystem to list triggered alarms"
                         " for.")
MY_ARGS = PARSER.parse_args()
cli.prompt_for_password(MY_ARGS)
SI = SmartConnect(host=MY_ARGS.host,
                  user=MY_ARGS.user,
                  pwd=MY_ARGS.password,
                  port=MY_ARGS.port)

atexit.register(Disconnect, SI)
INDEX = SI.content.searchIndex
if INDEX:
    HOST = INDEX.FindByUuid(datacenter=None, uuid=MY_ARGS.uuid, vmSearch=False)
    alarm.print_triggered_alarms(entity=HOST)
    # Since the above method will list all of the triggered alarms we will now
    # prompt the user for the entity info needed to reset an alarm from red
    # to green
    try:
        alarm_mor = raw_input("Enter the alarm_moref from above to reset the "
                              "alarm to green: ")
    except KeyboardInterrupt:
        # this is useful in case the user decides to quit and hits control-c
        print()
        raise SystemExit
    if alarm_mor:
        if alarm.reset_alarm(entity_moref=HOST._moId,
                             entity_type='HostSystem',
                             alarm_moref=alarm_mor.strip(),
                             service_instance=SI):
            print("Successfully reset alarm {0} to green.".format(alarm_mor))
else:
    print("Unable to create a SearchIndex.")
