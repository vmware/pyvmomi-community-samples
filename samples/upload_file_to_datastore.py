#!/usr/bin/env python

"""
Example for file upload to datastore
"""

import ssl
import requests
from pyVmomi import vim, vmodl
from tools import cli, service_instance


def main():
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.DATASTORE_NAME)
    parser.add_optional_arguments(cli.Argument.LOCAL_FILE_PATH, cli.Argument.REMOTE_FILE_PATH)
    args = parser.get_args()

    verify_cert = None
    if args.disable_ssl_verification:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        ssl_context.verify_mode = ssl.CERT_NONE
        verify_cert = False
        # disable urllib3 warnings
        requests.packages.urllib3.disable_warnings(
            requests.packages.urllib3.exceptions.InsecureRequestWarning)

    try:
        si = service_instance.connect(args)
        content = si.RetrieveContent()
        # session_manager = content.sessionManager

        # Get the list of all datacenters we have available to us
        datacenters_object_view = content.viewManager.CreateContainerView(
            content.rootFolder,
            [vim.Datacenter],
            True)

        # Find the datastore and datacenter we are using
        datacenter = None
        datastore = None
        for dc_obj in datacenters_object_view.view:
            datastores_object_view = content.viewManager.CreateContainerView(
                dc_obj,
                [vim.Datastore],
                True)
            for ds_obj in datastores_object_view.view:
                if ds_obj.info.name == args.datastore_name:
                    datacenter = dc_obj
                    datastore = ds_obj
        if not datacenter or not datastore:
            print("Could not find the datastore specified")
            raise SystemExit(-1)
        # Clean up the views now that we have what we need
        datastores_object_view.Destroy()
        datacenters_object_view.Destroy()

        # Build the url to put the file - https://hostname:port/resource?params
        if not args.remote_file_path.startswith("/"):
            remote_file = "/" + args.remote_file_path
        else:
            remote_file = args.remote_file_path
        resource = "/folder" + remote_file
        params = {"dsName": datastore.info.name,
                  "dcPath": datacenter.name}
        http_url = "https://" + args.host + ":443" + resource

        # Get the cookie built from the current session
        client_cookie = si._stub.cookie
        # Break apart the cookie into it's component parts - This is more than
        # is needed, but a good example of how to break apart the cookie
        # anyways. The verbosity makes it clear what is happening.
        cookie_name = client_cookie.split("=", 1)[0]
        cookie_value = client_cookie.split("=", 1)[1].split(";", 1)[0]
        cookie_path = client_cookie.split("=", 1)[1].split(";", 1)[1].split(
            ";", 1)[0].lstrip()
        cookie_text = " " + cookie_value + "; $" + cookie_path
        # Make a cookie
        cookie = dict()
        cookie[cookie_name] = cookie_text

        # Get the request headers set up
        headers = {'Content-Type': 'application/octet-stream'}

        # Get the file to upload ready, extra protection by using with against
        # leaving open threads
        with open(args.local_file_path, "rb") as file_data:
            # Connect and upload the file
            requests.put(http_url,
                         params=params,
                         data=file_data,
                         headers=headers,
                         cookies=cookie,
                         verify=verify_cert)
        print("uploaded the file")

    except vmodl.MethodFault as ex:
        print("Caught vmodl fault : " + ex.msg)
        raise SystemExit(-1)

    raise SystemExit(0)


if __name__ == "__main__":
    main()


# This may or may not be useful to the person who writes the download example
# def download(remote_file_path, local_file_path):
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

# This may or may not be useful to the person who tries to use a service
# request in the future

# Get the service request set up
#        service_request_spec = vim.SessionManager.HttpServiceRequestSpec(
#            method='httpPut', url=http_url)
#        ticket = session_manager.AcquireGenericServiceTicket(
#            service_request_spec)
