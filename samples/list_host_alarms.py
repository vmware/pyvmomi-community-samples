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
from tools import alarm, cli, service_instance


parser = cli.Parser()
# If you are unsure where to get the UUID of your HostSystem check out the
# MOB. For example in my lab I would connect directly to the host mob like so:
# https://10.12.254.10/mob/?moid=ha-host&doPath=hardware%2esystemInfo
parser.add_optional_arguments(cli.Argument.UUID, cli.Argument.ESX_IP)
args = parser.get_args()
si = service_instance.connect(args)

INDEX = si.content.searchIndex
if INDEX:
    if args.uuid:
        HOST = INDEX.FindByUuid(datacenter=None, uuid=args.uuid, vmSearch=False)
    elif args.esx_ip:
        HOST = INDEX.FindByIp(ip=args.esx_ip, vmSearch=False)

    if HOST is None:
        raise SystemExit("Unable to locate HostSystem.")

    alarm.print_triggered_alarms(entity=HOST)
    # Since the above method will list all of the triggered alarms we will now
    # prompt the user for the entity info needed to reset an alarm from red
    # to green
    try:
        alarm_mor = input("Enter the alarm_moref from above to reset the alarm to green: ")
    except KeyboardInterrupt:
        # this is useful in case the user decides to quit and hits control-c
        print()
        raise SystemExit
    if alarm_mor:
        if alarm.reset_alarm(entity_moref=HOST._moId,
                             entity_type='HostSystem',
                             alarm_moref=alarm_mor.strip(),
                             service_instance=si):
            print("Successfully reset alarm {0} to green.".format(alarm_mor))
else:
    print("Unable to create a SearchIndex.")
