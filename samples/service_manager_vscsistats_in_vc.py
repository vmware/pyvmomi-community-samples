#!/usr/bin/env python

from tools import cli, service_instance

"""
Example of fonnecting to the vScsiStats service provided
by vCenter Server's Service Manager
"""

__author__ = 'William Lam'


# Start program
def main():
    parser = cli.Parser()
    parser.add_optional_arguments(cli.Argument.ESX_IP)
    args = parser.get_args()
    serviceInstance = service_instance.connect(args)

    # "vmware.host." prefix is required when using VC
    location = "vmware.host." + args.esx_ip

    services = serviceInstance.content.serviceManager.QueryServiceList(
        location=[location])

    if services:
        for service in services:
            if service.serviceName == "VscsiStats":
                results = service.service.ExecuteSimpleCommand(
                    arguments=["FetchAllHistograms"])
                print(results)
    else:
        print("Unable to retrieve the service list from \
ESXi host. Pleaes ensure --esx_ip property is the FQDN or IP \
Address of the managed ESXi host in your vCenter Server")


# Start program
if __name__ == "__main__":
    main()
