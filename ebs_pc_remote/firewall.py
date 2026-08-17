import ctypes, subprocess, sys, os
from .config import CONTROL_PORT, DISCOVERY_PORT

def is_admin():
    try:return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:return False

def relaunch_admin():
    if os.name!="nt" or is_admin(): return True
    params=" ".join(f'"{a}"' for a in sys.argv)
    rc=ctypes.windll.shell32.ShellExecuteW(None,"runas",sys.executable,params,None,1)
    return rc>32

def ensure_firewall():
    if os.name!="nt" or not is_admin(): return False
    rules=[
        ("EBS PC Remote TCP","TCP",CONTROL_PORT),
        ("EBS PC Remote Discovery","UDP",DISCOVERY_PORT),
    ]
    for name,proto,port in rules:
        subprocess.run(["netsh","advfirewall","firewall","delete","rule",f"name={name}"],capture_output=True)
        subprocess.run(["netsh","advfirewall","firewall","add","rule",f"name={name}",
                        "dir=in","action=allow",f"protocol={proto}",f"localport={port}",
                        "profile=private"],capture_output=True)
    return True
