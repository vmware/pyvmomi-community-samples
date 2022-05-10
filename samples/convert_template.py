# IMPORT PACKAGES
from pyVmomi import vim, vmodl
from tools import cli, service_instance, pchelper
import ssl
import time

__author__ = 'mestredelpino'

# Get datacenter object
def get_datacenter(si,datacenter_name):
    content = si.RetrieveContent()
    datacenter = pchelper.get_obj(content, [vim.Datacenter], datacenter_name)
    return datacenter

# Get cluster object
def get_cluster(si, datacenter_name, cluster_name):
    content = si.RetrieveContent()
    datacenter = pchelper.get_obj(content, [vim.Datacenter], datacenter_name)
    for cluster in datacenter.hostFolder.childEntity:
        if cluster_name == cluster.name:
            return cluster

# Convert to/from template
def convert_template(convert_to, si, vm_name, datacenter_name, cluster_name):
    datacenter = get_datacenter(si, datacenter_name)
    cluster = get_cluster(si, datacenter_name,cluster_name)
    pool = cluster.resourcePool
    for each in datacenter.vmFolder.childEntity:
        try:
            if vm_name == each.name:
                if convert_to == "vm":
                    each.MarkAsVirtualMachine(pool)
                    print ("%s successfully converted into virtual machine"%vm_name)
                elif convert_to == "template":
                    try:
                        eachVM.PowerOff()
                        print ("Powering off VM")
                        time.sleep(5)
                        each.MarkAsTemplate()
                        print ("%s successfully converted into template"%vm_name)
                    except:
                        each.MarkAsTemplate()
                        print ("%s successfully converted into template"%vm_name)
            else:
                for eachVM in each.childEntity:
                    if vm_name == eachVM.name and convert_to == "vm":
                        eachVM.MarkAsVirtualMachine(pool)
                        print ("%s successfully converted into virtual machine"%vm_name)
                    if vm_name == eachVM.name and convert_to == "template":
                        try:
                            eachVM.PowerOff()
                            print ("Powering off VM")
                            time.sleep(5)
                            eachVM.MarkAsTemplate()
                            print ("%s successfully converted into template"%vm_name)
                        except:
                            eachVM.MarkAsTemplate()
                            print ("%s successfully converted into template"%vm_name)
        except:
            print ("Could not convert to {0}. Make sure the {0} exists and it has not converted into a {0} already".format(convert_to))

def main():
    parser = cli.Parser()
    CONVERT_TO = {
            'name_or_flags': ['--convert-to'],
            'options': {'action': 'store', 'help': 'Convert to template or vm'}
        }
    parser.add_required_arguments(cli.Argument.VM_NAME, cli.Argument.DATACENTER_NAME, cli.Argument.CLUSTER_NAME, CONVERT_TO)
    args = parser.get_args()
    if args.disable_ssl_verification:
      context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
      context.verify_mode = ssl.CERT_NONE
      si = service_instance.SmartConnect(host=args.host, user=args.user, pwd=args.password, sslContext=context)
    else:
        si = service_instance.connect(host=args.host, user=args.user, pwd=args.password)
    cluster = get_cluster(si, args.datacenter_name, args.cluster_name)
    convert_template(args.convert_to, si, args.vm_name, args.datacenter_name, args.cluster_name)

# Start program
if __name__ == "__main__":
    main()
