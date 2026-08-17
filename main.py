import sys, os
from ebs_pc_remote.util import load_identity
from ebs_pc_remote.discovery import DiscoveryService
from ebs_pc_remote.network import Server
from ebs_pc_remote.firewall import is_admin, relaunch_admin, ensure_firewall
from ebs_pc_remote.ui import MainWindow

def main():
    if os.name=="nt" and not is_admin():
        if relaunch_admin(): return
    ensure_firewall()
    ident=load_identity()
    holder={}
    app=None
    def ask(peer): return holder["app"].modern_accept(peer)
    def incoming(sess): holder["app"].incoming(sess)
    server=Server(ident,ask,incoming); server.start()
    discovery=DiscoveryService(ident)
    app=MainWindow(ident,discovery,server); holder["app"]=app
    discovery.on_update=lambda peers: app.after(0,lambda:app.update_peers(peers))
    discovery.start()
    app.mainloop()

if __name__=="__main__":
    main()
