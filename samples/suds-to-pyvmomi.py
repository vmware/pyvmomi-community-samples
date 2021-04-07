#!/usr/bin/env python

import suds
from tools import cli, service_instance

# suds-to-pyvmomi.py
#
# Some projects will want to incorporate pyVmomi into suds based projects. This
# sample shows how to take a suds cookie and inject it into pyVmomi so you may
# use pyVmomi and suds along side each other.

parser = cli.Parser()
args = parser.get_args()

url = "https://%s/sdk/vimService.wsdl" % args.host

print("Python suds...")
suds_client = suds.client.Client(url, location=url)
si = suds.sudsobject.Property("ServiceInstance")
si._type = "ServiceInstance"
sc = suds_client.service.RetrieveServiceContent(si)

suds_client.service.Login(sc.sessionManager,
                          userName=args.user,
                          password=args.password)


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


current_session = get_current_session(suds_client)

if current_session:
    print("current session id: %s" % current_session.key)
    cookies = suds_client.options.transport.cookiejar
    for cookie in cookies:
        print("cookie '%s' contents: %s" % (cookie.name, cookie.value))
else:
    print("not logged in")
    raise RuntimeError("this sample doesn't work if you can't authenticate")

# now to move the current session ID over to pyVmomi

VMWARE_COOKIE_NAME = 'vmware_soap_session'


def extract_vmware_cookie_suds(client):
    cookiejar = client.options.transport.cookiejar
    for cookie in cookiejar:
        if cookie.name == VMWARE_COOKIE_NAME:
            return '%s=%s' % (cookie.name, cookie.value)


# dynamically inject this method into the suds client:
suds_client.__class__.extract_vmware_cookie = extract_vmware_cookie_suds

print("=" * 80)
print("suds session to pyvmomi ")

# Unfortunately, you can't connect without a login in pyVmomi
si = service_instance.connect(args)

# logout the current session since we won't be using it.
si.content.sessionManager.Logout()

# inject the pyVmomi stub with the suds cookie values...
si._stub.cookie = suds_client.extract_vmware_cookie()

print("current suds session id: ")
print(get_current_session(suds_client).key)
print("\n")
print("current pyVmomi session id: %s")
print(si.content.sessionManager.currentSession.key)
print("\n")

# always clean up your sessions:
si.content.sessionManager.Logout()
