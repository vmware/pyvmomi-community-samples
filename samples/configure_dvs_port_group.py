# Written by Mahesh kumar and Pavan Bidkar
# GitHub: https://github.com/vmware/pyvmomi
# Email: kumahesh@vmware.com, pbidkar@vmware.com
#
# This code has been released under the terms of the Apache-2.0 license
# http://opensource.org/licenses/Apache-2.0
#
# Description: This sample exports, deletes and imports the
# distributed port group configuration of the given distributed switch
#
# Prerequisite: Dswitch with atleast one distributed port group configured
# for the datacenter

import atexit

from pyVim.connect import Disconnect, SmartConnectNoSSL, SmartConnect
from pyVmomi import vim, vmodl

from tools import cli


def get_args():
    """
    Adds additional args for the Dvs portgroup configuration
    """
    parser = cli.build_arg_parser()

    parser.add_argument('-ds', '--dvs-name',
                        required=True,
                        help=' Name of the distributed virtual switch')

    parser.add_argument('-pg', '--dvs-pg-name',
                        required=True,
                        help="Name of the distributed port group")
    my_args = parser.parse_args()
    return cli.prompt_for_password(my_args)


def get_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True
    )
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def configure_dvs_pg(service_instance, dvs_name, dv_pg_name):
    """
    Configures the distributed port group
    :param service_instance: Vcenter service instance
    :param dvs_name: Name of the distributed virtual switch
    :param dv_pg_name: Name of distributed virtual port group
    """
    # Retrieve the content
    content = service_instance.RetrieveContent()

    # get distributed Switch and its port group objects
    dvs = get_obj(content, [vim.DistributedVirtualSwitch], dvs_name)
    dv_pg = get_obj(content, [vim.dvs.DistributedVirtualPortgroup], dv_pg_name)
    print("The distributed virtual Switch is {0}" .format(dvs))
    print("The distributed port group is {0}".format(dv_pg))

    # construct selection sets
    selection_sets = []
    dv_pg_ss = vim.dvs.DistributedVirtualPortgroupSelection()
    dv_pg_ss.dvsUuid = dvs.uuid
    dv_pg_ss.portgroupKey.append(dv_pg.key)
    selection_sets.append(dv_pg_ss)
    print("The selected port group configurations  are {0}"
          .format(selection_sets))

    # Backup/Export the configuration
    entity_backup_config = service_instance.content\
        .dvSwitchManager\
        .DVSManagerExportEntity_Task(selection_sets)
    export_result = entity_backup_config.info.result
    print("The result of export configuration are {0}".format(export_result))

    # Destroy the port group configuration
    dv_pg.Destroy_Task()

    # Restore/Import port group configuration
    entity_restore_config = service_instance.content\
        .dvSwitchManager\
        .DVSManagerImportEntity_Task(export_result,
                                     'createEntityWithOriginalIdentifier')
    print("The result of restore configuration is {0}"
          .format(entity_restore_config.info.result))


def main():

    args = get_args()

    try:
        if args.disable_ssl_verification:
            service_instance = SmartConnectNoSSL(host=args.host,
                                                 user=args.user,
                                                 pwd=args.password,
                                                 port=args.port)
        else:
            service_instance = SmartConnect(host=args.host,
                                            user=args.user,
                                            pwd=args.password,
                                            port=args.port)

        atexit.register(Disconnect, service_instance)

        # call configuration of dvs port group
        configure_dvs_pg(service_instance, args.dvs_name, args.dvs_pg_name)

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : {0}".format(error.msg))
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
