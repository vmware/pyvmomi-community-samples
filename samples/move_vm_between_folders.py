from pyVim import connect
from pyVmomi import vim
import atexit
import sys
from time import sleep

def get_args():
    """ Just parse command line arguments using argparse module."""
    import argparse

    parser = argparse.ArgumentParser(
                                     description = "Argumens to specify VM and vCenter details:")
    parser.add_argument('-s', '--host',
                        required = True,
                        action = "store",
                        help = "ESXi or vCenter to connect")
    parser.add_argument('-p', '--port',
                        required = False,
                        type = int,
                        default = 443,
                        action = "store",
                        help='Port to use to connect to ESXi or vCenter')
    parser.add_argument('-u', '--user',
                        action="store",
                        required = True,
                        help = "Admin user to login to ESXi or vCenter")
    parser.add_argument('-P', '--password',
                        required = True,
                        action = "store",
                        help = "Password of user allowed to create VMs")
    parser.add_argument('-f', "--from-folder",
                        action="store",
                        required = False,
                        help = "Soruce folder.")
    parser.add_argument("-t", "--to-folder",
                        action = "store",
                        required = True,
                        help = "Destination folder")
    parser.add_argument("-n", "--vm-name",
                        required = False,
                        action = "store",
                        help = "Optional vm-name. If not specified then content of the whole source folder will be moved.")
    args = parser.parse_args()
    return args

def get_object_by_name(content, vimType, name):
    """ Search for Managed Object Referrence of type and name given starting from the root dir."""
    container = content.viewManager.CreateContainerView(content.rootFolder, vimType, True)
    for v in container.view:
        if v.name == name: return v
    return None

def get_service_instance(args):
    """ Connect to vSphere and return a Service Instance object."""
    try:
        si = connect.SmartConnect(host = args.host,
                                  pwd = args.password,
                                  port = args.port,
                                  user = args.user)
    except Exception:
        print "Cannot establish vSphere connection".
        sys.exit(1)
    atexit.register(connect.Disconnect, si)
    return si

def main():
    args = get_args()
    si = get_service_instance(args)

    to_move = []                # This will be passed to move operation.
    if args.from_folder:
        srcFolder = get_object_by_name(si.RetrieveContent(), [vim.Folder], args.from_folder)    # If no VM specified, then try to fine the source folder
        if srcFolder is None:
            print "Source folder {} not found".format(args.from_folder)
            sys.exit(1)
        elif "VirtualMachine" not in srcFolder.childType:          # vim.Folder.childType is a list of objects supported by this folder
            print "Only folders that can contain VMs are supported."
            sys.exit(1)
        to_move.extend(srcFolder.childEntity)
    elif args.vm_name:
        vmName = get_object_by_name(si.content, [vim.VirtualMachine], args.vm_name)
        to_move.append(vmName)
    else:
        print "You have to specify VM's name to move or folder which content should be moved."
        sys.exit(1)
    if not to_move:
        print "Source directory is empty. Nothing to move."
        sys.exit(0)
    destFolder = get_object_by_name(si.content, [vim.Folder], args.to_folder)
    if destFolder is None:
        try:
            destFolder = si.content.rootFolder.childEntity[0].vmFolder.CreateFolder(args.to_folder)     # create dest folder in the top level datacenter object
        except Exception:
            print "Cannot create target folder."
            sys.exit(2)
    try:
        task = destFolder.MoveIntoFolder_Task(to_move)      # Invoke the move operation passing a list of objects to move.
    except Exception:
        print "Move operation cannot be completed."
        sys.exit(3)
    print "Waiting fot task to complete",
    while task.info.state == vim.TaskInfo.State.running or task.info.state == vim.TaskInfo.State.queued:
        print ".",
        sleep(1)
    if task.info.state == vim.TaskInfo.State.error:
        print "\nCannot move content to destination directory."
        sys.exit(3)
    if task.info.state == vim.TaskInfo.State.success:
        print "\nAll is done. Have a good day."

if __name__ == '__main__':
    main()
