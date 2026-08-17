import json, os, socket, hashlib, random, string, platform
from pathlib import Path
from .config import DATA_DIR

IDENTITY_FILE = DATA_DIR / "identity.json"

def private_ipv4():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def is_private_ipv4(ip):
    try:
        import ipaddress
        return ipaddress.ip_address(ip).is_private
    except Exception:
        return False

def load_identity():
    if IDENTITY_FILE.exists():
        try:
            return json.loads(IDENTITY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    digits = "".join(random.choice(string.digits) for _ in range(9))
    ident = {
        "id": digits,
        "name": platform.node() or "Windows-PC",
        "created": True,
    }
    IDENTITY_FILE.write_text(json.dumps(ident, ensure_ascii=False, indent=2), encoding="utf-8")
    return ident

def format_id(v):
    v = "".join(c for c in str(v) if c.isdigit())[:9]
    return " ".join([v[:3], v[3:6], v[6:9]]).strip()

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
