#!/usr/bin/env python

import argparse
import cookielib
import getpass
import suds

import pyVim.connect as connect

# pyvmomi-to-suds.py
#
# Demonstrates how to move a session between the pyVmomi client and the
# generated SOAP suds client. We leverage the suds library's use of cookielib
# to manipulate its cookies to match the pyVmomi cookies. That causes vCenter
# to identify both clients as the same user.

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--host',
                    required=True,
                    action='store',
                    help='Remote host to connect to')

parser.add_argument('-u', '--user',
                    required=True,
                    action='store',
                    help='User name to use when connecting to host')

parser.add_argument('-p', '--password',
                    required=False,
                    action='store',
                    help='Password to use when connecting to host')

parser.add_argument('-o', '--port',
                    required=False,
                    action='store',
                    help="port to use, default 443", default=443)

args = parser.parse_args()
if args.password:
    password = args.password
else:
    password = getpass.getpass(
        prompt='Enter password for host %s and user %s: ' %
               (args.host, args.user))

url = "https://%s/sdk/vimService.wsdl" % args.host

client = suds.client.Client(url, location=url)


def get_current_session(client):
    si = suds.sudsobject.Property("ServiceInstance")
    si._type = "ServiceInstance"
    sc = client.service.RetrieveServiceContent(si)
    property_filter_spec = client.factory.create('ns0:PropertyFilterSpec')
    property_spec = client.factory.create('ns0:PropertySpec')
    property_spec.pathSet = ['currentSession']
    property_spec.type = "SessionManager"
    property_filter_spec.propSet = [property_spec]
    object_spec = client.factory.create('ns0:ObjectSpec')
    object_spec.obj = sc.sessionManager
    object_spec.skip = False
    property_filter_spec.objectSet = [object_spec]
    options = client.factory.create('ns0:RetrieveOptions')
    options.maxObjects = 1
    results = client.service.RetrievePropertiesEx(sc.propertyCollector,
                                                  specSet=[
                                                      property_filter_spec],
                                                  options=options)

    def get_property(self, name):
        for obj in self.objects:
            if not hasattr(obj, 'propSet'):
                return None
            for prop in obj.propSet:
                if prop.name == name:
                    return prop.val

    results.__class__.get_property = get_property
    return results.get_property('currentSession')


print "pyVmomi login... "

si = connect.SmartConnect(host=args.host,
                          user=args.user,
                          pwd=password,
                          port=int(args.port))

print "current session id: %s" % si.content.sessionManager.currentSession.key
pyvmomi_cookie = si._stub.cookie
print "current cookie contents: %s" % pyvmomi_cookie

VMWARE_COOKIE_NAME = 'vmware_soap_session'


def inject_vmware_cookie_suds(client, cookie_value, domain):
    cookie = cookielib.Cookie(0,
                              VMWARE_COOKIE_NAME,
                              cookie_value,
                              None,
                              None,
                              domain,
                              None,
                              None,
                              "/",
                              None,
                              None,
                              None,
                              None,
                              None,
                              None,
                              None,
                              None,)
    client.options.transport.cookiejar.set_cookie(cookie)


client.__class__.set_vmware_cookie = inject_vmware_cookie_suds

print "=" * 80
print "pyvmomi to suds"

si._stub.cookie = pyvmomi_cookie

# extracting the cookie value:
start_of_value = pyvmomi_cookie.index("=") + 1
end_of_value = pyvmomi_cookie.index(";")

cookie_value = pyvmomi_cookie[start_of_value:end_of_value]

session_id = si.content.sessionManager.currentSession.key
print "current pyVmomi session id: %s" % session_id

# injecting the cookie value:
client.set_vmware_cookie(cookie_value, args.host)
soap_session_id = get_current_session(client).key
print "current suds session id:    %s" % soap_session_id

assert session_id == soap_session_id
