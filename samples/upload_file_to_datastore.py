#!/usr/bin/env python

import requests 
from requests.auth import HTTPBasicAuth

import atexit
import cookielib
from pprint import pprint # used for debugging, not needed in production

from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim

from tools import cli



def get_args():
    parser = cli.build_arg_parser()
    parser.add_argument('-d', '--datastore',
                        required=True,
                        action='store',
                        help='Datastore name')
    parser.add_argument('-l', '--local_file',
                        required=True,
                        action='store',
                        help='Local disk path to file')
    parser.add_argument('-r', '--remote_file',
                        required=True,
                        action='store',
                        help='Path on datastore to place file')
    parser.add_argument('-S', '--disable_ssl_verification',
                        required=False,
                        action='store_true',
                        help='Disable ssl host certificate verification')
    args = parser.parse_args()

    return cli.prompt_for_password(args)
    
def main():
    
    args = get_args()

    try:
        service_instance = None
        try:
            service_instance = connect.SmartConnect(host=args.host,
                                                    user=args.user,
                                                    pwd=args.password,
                                                    port=int(args.port)) 
        except IOError, e:
            pass
        if not service_instance:
            print("Could not connect to the specified host using specified "
                  "username and password")
            return -1
        
        # Ensure that we cleanly disconnect in case our code dies
        atexit.register(connect.Disconnect, service_instance)

        content = service_instance.RetrieveContent()
        session_manager = content.sessionManager
      
        # Get the list of all datacenters we have available to us
        datacenters_object_view = content.viewManager.CreateContainerView(content.rootFolder, 
                                                           [vim.Datacenter], 
                                                           True)

        # Find the datastore and datacenter we are using
        datacenter = None
        datastore = None
        for dc in datacenters_object_view.view:
            datastores_object_view = content.viewManager.CreateContainerView(dc,
                                                           [vim.Datastore],
                                                           True)
            for ds in datastores_object_view.view:
                if ds.info.name == args.datastore:
                    datacenter = dc
                    datastore = ds
        if not datacenter or not datastore:
            print ("Could not find the datastore specified")
            return -1
        # Clean up the views now that we have what we need
        datastores_object_view.Destroy()
        datacenters_object_view.Destroy()

        # Build the url to put the file to - https://hostname:port/resource?params
        if not args.remote_file.startswith("/"):
            remote_file = "/" + args.remote_file
        else:
            remote_file = args.remote_file
        resource = "/folder" + remote_file
        params = {"dsName": datastore.info.name,
                    "dcPath": datacenter.name}
        http_url = "https://" + args.host + ":443" + resource

        pprint(http_url) # Debugging

        # Get the cookie built from the current session
        client_cookie = service_instance._stub.cookie
        pprint(client_cookie) # Debugging
        # Break apart the cookie into it's component parts
        cookie_name = client_cookie.split("=", 1)[0]
        cookie_value = client_cookie.split("=", 1)[1].split(";", 1)[0]
        cookie_path = client_cookie.split("=", 1)[1].split(";", 1)[1].split(";", 1)[0].lstrip()
        cookie_text = " " + cookie_value + "; $" + cookie_path
        # Make a cookie
        cookie = dict()
        cookie[cookie_name] = cookie_text
                                    

        # Get the request headers set up
        headers =   {'Content-Type': 'application/octet-stream'}
        
        # Get the file to upload ready, extra protection by using with against leaving open threads
        with open(args.local_file, "rb") as f:
            # Connect and upload the file
            request = requests.put( http_url, 
                                    params=params,  
                                    data=f, 
                                    headers=headers, 
                                    cookies=cookie, 
                                    verify=args.disable_ssl_verification )
            pprint(request.status_code) # Debugging


    except vmodl.MethodFault, e:
        pass
        print "Caught vmodl fault : " + e.msg
        return -1

    return 0


if __name__== "__main__":
    main()


# This may or may not be useful to the person who writes the download example
#def download(remote_file_path, local_file_path):
#    resource = "/folder/%s" % remote_file_path.lstrip("/")
#    url = self._get_url(resource)
#    
#    if sys.version_info >= (2, 6):
#        resp = self._do_request(url)
#        CHUNK = 16 * 1024
#        fd = open(local_file_path, "wb")
#        while True:
#            chunk = resp.read(CHUNK)
#            if not chunk: break
#            fd.write(chunk)
#        fd.close()
#    else:
#        urllib.urlretrieve(url, local_file_path)
#

# This may or may not be useful to the person who tries to use a service request in the future

        # Get the service request set up
#        service_request_spec = vim.SessionManager.HttpServiceRequestSpec(method='httpPut', url=http_url)
#        ticket = session_manager.AcquireGenericServiceTicket(service_request_spec)
