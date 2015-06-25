#!/usr/bin/env python

import code
import atexit

from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim

from tools import cli
from tools import vm


def get_view(content, vimtype):
    """
    Get the view of an object
    """
    objview = content.viewManager.CreateContainerView(content.rootFolder,
                                                      vimtype, True)
    view = objview.view
    objview.Destroy()
    return view


def auth():
    """
    Authentication to the server
    """

    args = cli.get_args()

    try:
        si = connect.SmartConnect(host=args.host,
                                  user=args.user,
                                  pwd=args.password,
                                  port=int(args.port))

        if not si:
            print("Could not connect to the specified host using specified "
                  "username and password")
            return None

        atexit.register(connect.Disconnect, si)

    except vmodl.MethodFault, e:
        print "Caught vmodl fault : " + e.msg
        return None

    return si.RetrieveContent()


def main():
    """
    Contect to the server (vCenter or ESXi host) retrieve the content then
    drop into a prompt.
    """
    global content
    content = auth()
    print("== content -> ", content)
    print("'content = auth()' when re-auth needed")

    code.interact(local=globals())
    return 0

# Start program
if __name__ == "__main__":
    main()
