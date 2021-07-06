#!/usr/bin/env python
"""
 Written by Fabian Chong
 Github: https://github.com/feiming

 Script retrieve Vsphere events for logging

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
""
"""

from datetime import datetime
import time
import json

from tools import cli, service_instance
from pyVmomi import vim


def print_event(event, output_json=False):
    if output_json:
        data = event.__dict__
        for k, v in data.items():
            if isinstance(v, datetime):
                data[k] = v.isoformat()
            if hasattr(v, "name"):
                data[k] = v.name

        print(json.dumps(data))
    else:
        print(event)


def main():
    parser = cli.Parser()
    parser.add_custom_argument(
        "--startTime",
        help="Events start time, ISO format or now",
        default="now",
    )
    parser.add_custom_argument(
        "--endTime",
        help="Events end time, ISO format or now.",
    )
    parser.add_custom_argument(
        "--pageSize",
        help="Events page size",
        default=1000,
        type=int,
    )
    parser.add_custom_argument(
        "--interval",
        help="Seconds between update. If set, it will continue loop infintely",
        type=int,
    )
    parser.add_custom_argument(
        "--eventType",
        help="filter on certain events,refer: \
            https://pubs.vmware.com/vsphere-6-5/topic/com.vmware.wssdk.smssdk.doc/vim.event.EventFilterSpec.html",
        nargs="+",
        default=[],
    )
    parser.add_custom_argument(
        "--json", default=False, action="store_true", help="Output to JSON"
    )
    args = parser.get_args()
    si = service_instance.connect(args)

    time_filter = vim.event.EventFilterSpec.ByTime()
    time_filter.beginTime = (
        datetime.now()
        if args.startTime.lower() == "now"
        else datetime.fromisoformat(args.startTime)
    )
    if args.endTime:
        time_filter.endTime = (
            datetime.now()
            if args.endTime.lower() == "now"
            else datetime.fromisoformat(args.endTime)
        )

    filter_spec = vim.event.EventFilterSpec(
        eventTypeId=args.eventType, time=time_filter
    )

    si = service_instance.connect(args)
    eventManager = si.content.eventManager
    event_collector = eventManager.CreateCollectorForEvents(filter_spec)

    while True:
        events = event_collector.ReadNextEvents(args.pageSize)
        if len(events) == 0:
            if args.interval:
                time.sleep(args.interval)
            else:
                break
        else:
            for event in events:
                print_event(event, args.json)


# Start program
if __name__ == "__main__":
    main()
