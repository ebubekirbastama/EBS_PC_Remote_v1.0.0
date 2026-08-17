import os, json, struct, threading
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def _recv_exact(sock, n):
    out = bytearray()
    while len(out) < n:
        part = sock.recv(n-len(out))
        if not part:
            raise ConnectionError("Bağlantı kapandı")
        out.extend(part)
    return bytes(out)

def send_plain(sock, obj):
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode()
    sock.sendall(struct.pack("!I", len(raw)) + raw)

def recv_plain(sock, limit=1024*1024):
    n = struct.unpack("!I", _recv_exact(sock, 4))[0]
    if n > limit:
        raise ValueError("Handshake paketi fazla büyük")
    return json.loads(_recv_exact(sock, n).decode("utf-8"))

def new_keypair():
    priv = ec.generate_private_key(ec.SECP256R1())
    pub = priv.public_key().public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    return priv, pub

def derive_key(priv, peer_pub_bytes, salt):
    peer = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), peer_pub_bytes)
    shared = priv.exchange(ec.ECDH(), peer)
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"EBS-PC-REMOTE-v1",
    ).derive(shared)

class SecureChannel:
    def __init__(self, sock, key):
        self.sock = sock
        try:
            import socket
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        except Exception:
            pass
        self.aes = AESGCM(key)
        self.send_counter = 0
        self.recv_counter = -1
        self.lock = threading.Lock()

    def send(self, kind, meta=None, payload=b""):
        meta = meta or {}
        header = json.dumps({"kind":kind, "meta":meta}, ensure_ascii=False, separators=(",", ":")).encode()
        inner = struct.pack("!I", len(header)) + header + payload
        with self.lock:
            ctr = self.send_counter
            self.send_counter += 1
            nonce = os.urandom(4) + ctr.to_bytes(8, "big")
            enc = self.aes.encrypt(nonce, inner, b"EBS1")
            body = nonce + enc
            self.sock.sendall(struct.pack("!I", len(body)) + body)

    def recv(self, max_packet=32*1024*1024):
        n = struct.unpack("!I", _recv_exact(self.sock, 4))[0]
        if n < 28 or n > max_packet:
            raise ValueError("Geçersiz şifreli paket boyutu")
        body = _recv_exact(self.sock, n)
        nonce, enc = body[:12], body[12:]
        ctr = int.from_bytes(nonce[4:], "big")
        if ctr <= self.recv_counter:
            raise ValueError("Replay paketi reddedildi")
        inner = self.aes.decrypt(nonce, enc, b"EBS1")
        self.recv_counter = ctr
        hlen = struct.unpack("!I", inner[:4])[0]
        h = json.loads(inner[4:4+hlen].decode("utf-8"))
        return h["kind"], h.get("meta", {}), inner[4+hlen:]
