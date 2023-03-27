#!/usr/bin/env python
"""
Written by camrossi
Github: https://github.com/camrossi
Note: Example code For testing purposes only
This code has been released under the terms of the Apache-2.0 license
http://opensource.org/licenses/Apache-2.0
"""
import sys
from pyVmomi import vim
from tools import cli, service_instance,pchelper, tasks


def main():
    parser = cli.Parser()
    parser.add_custom_argument('--dvswitch-name', required=True,
                               help='name of the dvswitch', default='all')   
    args = parser.get_args()
    si = service_instance.connect(args)
    content = si.RetrieveContent()
    dvs = pchelper.search_for_obj(content, [vim.DistributedVirtualSwitch], args.dvswitch_name)
    for span in dvs.config.vspanSession:
        configVersion = dvs.config.configVersion
        print("remove Span Session", span.key)
        s_spec = vim.dvs.VmwareDistributedVirtualSwitch.VspanConfigSpec(vspanSession=span, operation="remove")
        c_spec = vim.dvs.VmwareDistributedVirtualSwitch.ConfigSpec(vspanConfigSpec=[s_spec], configVersion=configVersion)
        t = dvs.ReconfigureDvs_Task(c_spec)
        tasks.wait_for_tasks(si, [t])
# Main section
if __name__ == "__main__":
    sys.exit(main())
