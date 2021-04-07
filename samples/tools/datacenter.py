"""
Written by Michael Rice
Github: https://github.com/michaelrice
Website: https://michaelrice.github.io/
Blog: http://www.errr-online.com/
This code has been released under the terms of the Apache 2.0 license
http://opensource.org/licenses/Apache-2.0

This sample can be run directly to create a datacenter, but may be more
useful to import into another project where you need to create a datacenter
then use that object to further configure things like create a cluster or
adding resources like HostSystems.
"""
from pyVmomi import vim


def create_datacenter(dc_name=None, service_instance=None, folder=None):
    """
    Creates a new datacenter with the given name.
    Any % (percent) character used in this name parameter must be escaped,
    unless it is used to start an escape sequence. Clients may also escape
    any other characters in this name parameter.

    An entity name must be a non-empty string of
    less than 80 characters. The slash (/), backslash (\\) and percent (%)
    will be escaped using the URL syntax. For example, %2F

    This can raise the following exceptions:
    vim.fault.DuplicateName
    vim.fault.InvalidName
    vmodl.fault.NotSupported
    vmodl.fault.RuntimeFault
    ValueError raised if the name len is > 79
    https://github.com/vmware/pyvmomi/blob/master/docs/vim/Folder.rst

    Required Privileges
    Datacenter.Create

    :param folder: Folder object to create DC in. If None it will default to
                   rootFolder
    :param dc_name: Name for the new datacenter.
    :param service_instance: ServiceInstance connection to a given vCenter
    :return:
    """
    if len(dc_name) > 79:
        raise ValueError("The name of the datacenter must be under "
                         "80 characters.")
    if folder is None:
        folder = service_instance.content.rootFolder

    if folder is not None and isinstance(folder, vim.Folder):
        dc_moref = folder.CreateDatacenter(name=dc_name)
        return dc_moref


if __name__ == "__main__":
    import atexit
    from pyVim import connect
    import cli
    PARSER = cli.build_arg_parser()
    PARSER.add_argument("-n", "--name",
                        required=True,
                        action="store",
                        help="Name of the Datacenter to create.")
    MY_ARGS = PARSER.parse_args()
    cli.prompt_for_password(MY_ARGS)
    SI = connect.SmartConnect(host=MY_ARGS.host,
                              user=MY_ARGS.user,
                              pwd=MY_ARGS.password,
                              port=MY_ARGS.port)
    create_datacenter(dc_name=MY_ARGS.name, service_instance=SI)
    atexit.register(connect.Disconnect, SI)
