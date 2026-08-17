import socket, json, threading, time
from .config import DISCOVERY_PORT, CONTROL_PORT, BROADCAST_INTERVAL, PEER_TTL, VERSION
from .util import private_ipv4, is_private_ipv4

class DiscoveryService:
    def __init__(self, identity, on_update=None):
        self.identity = identity
        self.on_update = on_update
        self.peers = {}
        self.running = False

    def start(self):
        if self.running: return
        self.running = True
        threading.Thread(target=self._announce, daemon=True).start()
        threading.Thread(target=self._listen, daemon=True).start()
        threading.Thread(target=self._clean, daemon=True).start()

    def stop(self): self.running = False

    def _packet(self):
        return json.dumps({
            "magic":"EBS_PC_REMOTE",
            "version":VERSION,
            "id":self.identity["id"],
            "name":self.identity["name"],
            "ip":private_ipv4(),
            "port":CONTROL_PORT,
        }, separators=(",", ":")).encode()

    def _announce(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while self.running:
            try: s.sendto(self._packet(), ("255.255.255.255", DISCOVERY_PORT))
            except Exception: pass
            time.sleep(BROADCAST_INTERVAL)

    def _listen(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", DISCOVERY_PORT))
        s.settimeout(1)
        while self.running:
            try:
                data, addr = s.recvfrom(8192)
                o = json.loads(data.decode())
                if o.get("magic") != "EBS_PC_REMOTE": continue
                if o.get("id") == self.identity["id"]: continue
                ip = addr[0]
                if not is_private_ipv4(ip): continue
                o["ip"] = ip
                o["_seen"] = time.time()
                self.peers[o["id"]] = o
                if self.on_update: self.on_update(dict(self.peers))
            except socket.timeout: pass
            except Exception: pass
        s.close()

    def _clean(self):
        while self.running:
            now = time.time()
            changed = False
            for k in list(self.peers):
                if now - self.peers[k].get("_seen", 0) > PEER_TTL:
                    del self.peers[k]; changed=True
            if changed and self.on_update: self.on_update(dict(self.peers))
            time.sleep(1)
