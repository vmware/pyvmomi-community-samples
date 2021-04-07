#!/usr/bin/env python
"""Written by Humayun Jamal
Github: https://github.com/humayunjamal



Example script to configure Auto Restart Settings for Esxi Host
and also enable the auto restart settings of virtual machines
(which are powered on at the time of script execution)
running on the host in a random order.
This scrpt can be tailored to adjust more settings within
"""
import sys
from pyVmomi import vim
from tools import cli, service_instance
sys.dont_write_bytecode = True

__author__ = 'humayunjamal'


def get_hosts(conn):
    print("Getting All hosts Objects")
    content = conn.RetrieveContent()
    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.HostSystem], True)
    hosts = list(container.view)
    return hosts


def action_hosts(comma_list, connection, defstartdelay):
    print("Actioning the Provided Hosts")
    acthosts = comma_list.split(",")
    allhosts = get_hosts(connection)
    host_names = [h.name for h in allhosts]
    for action_host in acthosts:
        if action_host not in host_names:
            print("The host cant be found " + action_host)

    for host in allhosts:
        if host.name in acthosts:
            enable_autorestart(host, defstartdelay)


def enable_autorestart(host, defstartdelay):
    print("Enabling Auto Restart for Host")
    print("The Selected Host is \n" + host.name)
    print("Setting the Selected Host default AutoStartManager")
    host_def_settings = vim.host.AutoStartManager.SystemDefaults()
    host_def_settings.enabled = True
    host_def_settings.startDelay = int(defstartdelay)
    print("virtual machines and applying Auto Start settings")
    order = 1
    for vhost in host.vm:
        spec = host.configManager.autoStartManager.config
        spec.defaults = host_def_settings
        auto_power_info = vim.host.AutoStartManager.AutoPowerInfo()
        auto_power_info.key = vhost
        print("The VM   is updated if On" + vhost.name)
        print("VM Status is " + vhost.runtime.powerState)
        if vhost.runtime.powerState == "poweredOff":
            auto_power_info.startAction = 'None'
            auto_power_info.waitForHeartbeat = 'no'
            auto_power_info.startDelay = -1
            auto_power_info.startOrder = -1
            auto_power_info.stopAction = 'None'
            auto_power_info.stopDelay = -1
        elif vhost.runtime.powerState == "poweredOn":
            # note use of constant instead of string
            auto_power_info.startAction = 'powerOn'
            auto_power_info.startDelay = -1
            auto_power_info.startOrder = -1
            auto_power_info.stopAction = 'None'
            auto_power_info.stopDelay = -1
            auto_power_info.waitForHeartbeat = 'no'
            spec.powerInfo = [auto_power_info]
            order = order + 1
            print("Apply Setting to Host")
            host.configManager.autoStartManager.ReconfigureAutostart(spec)


# MAIN
parser = cli.Parser()
parser.add_custom_argument('--listallhosts', required=False, action='store_true')
parser.add_custom_argument('--actionhosts',
                           help='Comma delimeted list of VHosts which needs to be actioned',
                           required=False, action='store')
parser.add_custom_argument('--defstartdelay', help='Default Startup Delay',
                           default=10, required=False, action='store')
args = parser.get_args()
print("Starting")
print("Getting Config")
print("Connecting to vSphere")
si = service_instance.connect(args)

if args.listallhosts is True:
    vSpherehosts = get_hosts(si)
    print("All the Hosts Attached are :\n")
    for host in vSpherehosts:
        print("\n" + host.name)

if args.actionhosts is not None:
    action_hosts(
        args.actionhosts, si, args.defstartdelay)
