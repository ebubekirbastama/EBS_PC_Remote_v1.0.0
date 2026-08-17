import socket, os, base64, threading
from .config import CONTROL_PORT, VERSION
from .crypto_channel import send_plain, recv_plain, new_keypair, derive_key, SecureChannel
from .util import is_private_ipv4
from .session import RemoteSession

class Server:
    def __init__(self, identity, ask_accept, on_session):
        self.identity=identity
        self.ask_accept=ask_accept
        self.on_session=on_session
        self.running=False
        self.sock=None

    def start(self):
        if self.running:return
        self.running=True
        self.sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.sock.bind(("",CONTROL_PORT)); self.sock.listen(8)
        threading.Thread(target=self._loop,daemon=True).start()

    def _loop(self):
        while self.running:
            try:
                c,addr=self.sock.accept()
                threading.Thread(target=self._handle,args=(c,addr),daemon=True).start()
            except Exception:
                if self.running: continue

    def _handle(self,c,addr):
        try:
            if not is_private_ipv4(addr[0]): raise PermissionError("LAN dışı istemci reddedildi")
            hello=recv_plain(c)
            if hello.get("magic")!="EBS_PC_REMOTE": raise ValueError("Geçersiz istemci")
            peer={"id":hello["id"],"name":hello.get("name","PC"),"ip":addr[0]}
            if not self.ask_accept(peer):
                send_plain(c,{"accepted":False}); c.close(); return
            priv,pub=new_keypair(); salt=os.urandom(32)
            send_plain(c,{"accepted":True,"id":self.identity["id"],"name":self.identity["name"],
                          "pub":base64.b64encode(pub).decode(),"salt":base64.b64encode(salt).decode()})
            client_pub=base64.b64decode(hello["pub"])
            key=derive_key(priv,client_pub,salt)
            sess=RemoteSession(SecureChannel(c,key),peer,incoming=True)
            self.on_session(sess)
        except Exception:
            try:c.close()
            except Exception:pass

class Client:
    @staticmethod
    def connect(identity, peer, timeout=8):
        c=socket.create_connection((peer["ip"], int(peer.get("port",CONTROL_PORT))),timeout=timeout)
        priv,pub=new_keypair()
        send_plain(c,{"magic":"EBS_PC_REMOTE","version":VERSION,"id":identity["id"],"name":identity["name"],
                      "pub":base64.b64encode(pub).decode()})
        ans=recv_plain(c)
        if not ans.get("accepted"):
            c.close(); raise PermissionError("Karşı bilgisayar bağlantıyı reddetti")
        salt=base64.b64decode(ans["salt"]); server_pub=base64.b64decode(ans["pub"])
        key=derive_key(priv,server_pub,salt)
        p={"id":ans["id"],"name":ans.get("name",peer.get("name","PC")),"ip":peer["ip"]}
        return RemoteSession(SecureChannel(c,key),p,incoming=False)
