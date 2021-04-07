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

"""
Example for configuring a distributed port group
"""

from pyVmomi import vim, vmodl
from tools import cli, service_instance, pchelper


def configure_dvs_pg(si, dvs_name, dv_pg_name):
    """
    Configures the distributed port group
    :param si: Vcenter service instance
    :param dvs_name: Name of the distributed virtual switch
    :param dv_pg_name: Name of distributed virtual port group
    """
    # Retrieve the content
    content = si.RetrieveContent()

    # get distributed Switch and its port group objects
    dvs = pchelper.get_obj(content, [vim.DistributedVirtualSwitch], dvs_name)
    dv_pg = pchelper.get_obj(content, [vim.dvs.DistributedVirtualPortgroup], dv_pg_name)
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
    entity_backup_config = si.content\
        .dvSwitchManager\
        .DVSManagerExportEntity_Task(selection_sets)
    export_result = entity_backup_config.info.result
    print("The result of export configuration are {0}".format(export_result))

    # Destroy the port group configuration
    dv_pg.Destroy_Task()

    # Restore/Import port group configuration
    entity_restore_config = si.content\
        .dvSwitchManager\
        .DVSManagerImportEntity_Task(export_result,
                                     'createEntityWithOriginalIdentifier')
    print("The result of restore configuration is {0}"
          .format(entity_restore_config.info.result))


def main():
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.DVS_NAME, cli.Argument.DVS_PORT_GROUP_NAME)
    args = parser.get_args()
    si = service_instance.connect(args)

    try:
        # call configuration of dvs port group
        configure_dvs_pg(si, args.dvs_name, args.dvs_pg_name)

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : {0}".format(error.msg))
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
