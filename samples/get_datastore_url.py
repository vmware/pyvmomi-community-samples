# IMPORT PACKAGES
from pyVmomi import vim, vmodl
from tools import cli, service_instance, pchelper
import ssl

def get_datacenter(si,datacenter_name):
    content = si.RetrieveContent()
    datacenter = pchelper.get_obj(content, [vim.Datacenter], datacenter_name)
    return datacenter

def get_datastore(si,datacenter_name,datastore_name):
    content = si.RetrieveContent()
    datacenter = pchelper.get_obj(content, [vim.Datacenter], datacenter_name)
    for datastore in datacenter.datastoreFolder.childEntity:
        if datastore.name == datastore_name:
            return datastore

def get_cluster(si, datacenter_name, cluster_name):
    content = si.RetrieveContent()
    datacenter = pchelper.get_obj(content, [vim.Datacenter], datacenter_name)
    for cluster in datacenter.hostFolder.childEntity:
        if cluster_name == cluster.name:
            return cluster

def main():
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.CLUSTER_NAME,cli.Argument.DATASTORE_NAME, cli.Argument.DATACENTER_NAME)
    args = parser.get_args()
    if args.disable_ssl_verification:
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_NONE
        si = service_instance.SmartConnect(host=args.host, user=args.user, pwd=args.password, sslContext=context)
    else:
        si = service_instance.SmartConnect(host=args.host, user=args.user, pwd=args.password)
    cluster = get_cluster(si, args.datacenter_name, args.cluster_name)
    datastore = get_datastore(si,args.datacenter_name,args.datastore_name)
    print (datastore.info.url)

# Start program
if __name__ == "__main__":
    main()


# --host "vcenter.magrathea.lab" --user "administrator@magrathea.lab" --password "Qweasd!!12" --datacenter-name "HomeLab" --datastore-name "DiscoSTU" -nossl