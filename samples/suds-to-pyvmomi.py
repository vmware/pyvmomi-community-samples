#!/usr/bin/env python

import argparse
import getpass
import suds

import pyVim.connect as connect

# suds-to-pyvmomi.py
#
# Some projects will want to incorporate pyVmomi into suds based projects. This
# sample shows how to take a suds cookie and inject it into pyVmomi so you may
# use pyVmomi and suds along side each other.

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--host',
                    required=True,
                    action='store',
                    help='Remote host to connect to')
parser.add_argument('-o', '--port',
                    required=False,
                    action='store',
                    help="port to use, default 443",
                    default=443)
parser.add_argument('-u', '--user',
                    required=True,
                    action='store',
                    help='User name to use when connecting to host')
parser.add_argument('-p', '--password',
                    required=False,
                    action='store',
                    help='Password to use when connecting to host')

args = parser.parse_args()
if args.password:
    password = args.password
else:
    password = getpass.getpass(
        prompt='Enter password for host %s and user %s: ' %
               (args.host, args.user))

url = "https://%s/sdk/vimService.wsdl" % args.host

print "Python suds..."
client = suds.client.Client(url, location=url)
si = suds.sudsobject.Property("ServiceInstance")
si._type = "ServiceInstance"
sc = client.service.RetrieveServiceContent(si)

client.service.Login(sc.sessionManager,
                     userName=args.user,
                     password=password)


def get_current_session(client):
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


current_session = get_current_session(client)

if current_session:
    print "current session id: %s" % current_session.key
    cookies = client.options.transport.cookiejar
    for cookie in cookies:
        print "cookie '%s' contents: %s" % (cookie.name, cookie.value)
else:
    print "not logged in"
    raise RuntimeError("this sample doesn't work if you can't authenticate")

# now to move the current session ID over to pyVmomi

VMWARE_COOKIE_NAME = 'vmware_soap_session'


def extract_vmware_cookie_suds(client):
    cookiejar = client.options.transport.cookiejar
    for cookie in cookiejar:
        if cookie.name == VMWARE_COOKIE_NAME:
            return '%s=%s' % (cookie.name, cookie.value)


# dynamically inject this method into the suds client:
client.__class__.extract_vmware_cookie = extract_vmware_cookie_suds

print "=" * 80
print "suds session to pyvmomi "

# Unfortunately, you can't connect without a login in pyVmomi
si = connect.SmartConnect(host=args.host,
                          user=args.user,
                          pwd=password,
                          port=int(args.port))

# logout the current session since we won't be using it.
si.content.sessionManager.Logout()

# inject the pyVmomi stub with the suds cookie values...
si._stub.cookie = client.extract_vmware_cookie()

print "current suds session id: "
print get_current_session(client).key
print
print "current pyVmomi session id: %s"
print si.content.sessionManager.currentSession.key
print

# always clean up your sessions:
si.content.sessionManager.Logout()
