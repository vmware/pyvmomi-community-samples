#!/usr/bin/env python
# William lam
# www.virtuallyghetto.com

import sys,re,os,urllib,urllib2,base64,syslog,socket

# vCenter server
vcenter_server = "vcenter51-1.primp-industries.com"

# vCenter Cluster path
cluster = "datacenter/host/cluster"

# vCenter credentials using encoded base64 password
vc_username = "vcjoin"
vc_encodedpassword = "TXlTdXBlckR1cGVyU2VjcmV0UGFzc3dvcmRZbw=="
vc_password = base64.b64decode(vc_encodedpassword)

# ESX(i) credentials using encoded base64 password
host_username = "root"
host_encodedpasssword = "dm13YXJl"
host_password = base64.b64decode(host_encodedpasssword)

### DO NOT EDIT PAST HERE ###

# vCenter mob URL for findByInventoryPath
url = "https://" + vcenter_server + "/mob/?moid=SearchIndex&method=findByInventoryPath"

# Create global variables
global passman,authhandler,opener,req,page,page_content,nonce,headers,cookie,params,e_params,syslogGhetto,clusterMoRef

# syslog key for eaiser troubleshooting
syslogGhetto = 'GHETTO-JOIN-VC'

syslog.syslog(syslogGhetto + ' Starting joinvCenter process - ' + url)

# Code to build opener with HTTP Basic Authentication
try:
        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passman.add_password(None,url,vc_username,vc_password)
        authhandler = urllib2.HTTPBasicAuthHandler(passman)
        opener = urllib2.build_opener(authhandler)
        urllib2.install_opener(opener)
except IOError, e:
        opener.close()
        syslog.syslog(syslogGhetto + ' Failed HTTP Basic Authentication!')
        sys.exit(1)
else:
        syslog.syslog(syslogGhetto + ' Succesfully built HTTP Basic Authentication')

# Code to capture required page data and cookie required for post back to meet CSRF requirements
# Thanks to user klich - http://communities.vmware.com/message/1722582#1722582
try:
        req = urllib2.Request(url)
        page = urllib2.urlopen(req)
        page_content= page.read()
except IOError, e:
        opener.close()
        syslog.syslog(syslogGhetto + ' Failed to retrieve MOB data')
        sys.exit(1)
else:
        syslog.syslog(syslogGhetto + ' Succesfully requested MOB data')

# regex to get the vmware-session-nonce value from the hidden form entry
reg = re.compile('name="vmware-session-nonce" type="hidden" value="?([^\s^"]+)"')
nonce = reg.search(page_content).group(1)

# get the page headers to capture the cookie
headers = page.info()
cookie = headers.get("Set-Cookie")

# Code to search for vCenter Cluster
params = {'vmware-session-nonce':nonce,'inventoryPath':cluster}
e_params = urllib.urlencode(params)
req = urllib2.Request(url, e_params, headers={"Cookie":cookie})
page = urllib2.urlopen(req).read()

clusterMoRef = re.search('domain-c[0-9]*',page)
if clusterMoRef:
        syslog.syslog(syslogGhetto + ' Succesfully located cluster "' + cluster + '"!')
else:
        opener.close()
        syslog.syslog(syslogGhetto + ' Failed to find cluster "' + cluster + '"!')
        sys.exit(1)

# Code to compute SHA1 hash
cmd = "openssl x509 -sha1 -in /etc/vmware/ssl/rui.crt -noout -fingerprint"
tmp = os.popen(cmd)
tmp_sha1 = tmp.readline()
tmp.close()
s1 = re.split('=',tmp_sha1)
s2 = s1[1]
s3 = re.split('\n', s2)
sha1 = s3[0]

if sha1:
        syslog.syslog(syslogGhetto + ' Succesfully computed SHA1 hash: "' + sha1 + '"!')
else:
        opener.close()
        syslog.syslog(syslogGhetto + ' Failed to compute SHA1 hash!')
        sys.exit(1)

# Code to create ConnectHostSpec
xml = '<spec xsi:type="HostConnectSpec"><hostName>%hostname</hostName><sslThumbprint>%sha</sslThumbprint><userName>%user</userName><password>%pass</password><force>1</force></spec>'

# Code to extract IP Address to perform DNS lookup to add FQDN to vCenter
hostip = socket.gethostbyname(socket.gethostname())

if hostip:
        syslog.syslog(syslogGhetto + ' Successfully extracted IP Address ' + hostip.strip())
else:
        opener.close()
        syslog.syslog(syslogGhetto + ' Failed to extract IP Address!')
        sys.exit(1)

try:
        host = socket.getnameinfo((hostip, 0), 0)[0]
except IOError, e:
        syslog.syslog(syslogGhetto + ' Failed to perform DNS lookup for ' + hostipt.strip())
        sys.exit(1)
else:
        syslog.syslog(syslogGhetto + ' Successfully performed DNS lookup for ' + hostip.strip() + ' is ' + host)

xml = xml.replace("%hostname",host)
xml = xml.replace("%sha",sha1)
xml = xml.replace("%user",host_username)
xml = xml.replace("%pass",host_password)

# Code to join host to vCenter Cluster
try:
        url = "https://" + vcenter_server + "/mob/?moid=" + clusterMoRef.group() + "&method=addHost"
        params = {'vmware-session-nonce':nonce,'spec':xml,'asConnected':'1','resourcePool':'','license':''}
    syslog.syslog(syslogGhetto + ' ' + url)
        e_params = urllib.urlencode(params)
        req = urllib2.Request(url, e_params, headers={"Cookie":cookie})
        page = urllib2.urlopen(req).read()
except IOError, e:
        opener.close()
        syslog.syslog(syslogGhetto + ' Failed to join vCenter!')
        syslog.syslog(syslogGhetto + ' HOSTNAME: ' + host)
        syslog.syslog(syslogGhetto + ' USERNAME: ' + host_username)
        #syslog.syslog(syslogGhetto + ' PASSWORD: ' + host_password)
        sys.exit(1)
else:
        syslog.syslog(syslogGhetto + ' Succesfully joined vCenter!')
        syslog.syslog(syslogGhetto + ' Logging off vCenter')
        url = "https://" + vcenter_server + "/mob/?moid=SessionManager&method=logout"
        params = {'vmware-session-nonce':nonce}
        e_params = urllib.urlencode(params)
        req = urllib2.Request(url, e_params, headers={"Cookie":cookie})
        page = urllib2.urlopen(req).read()
        sys.exit(0)
