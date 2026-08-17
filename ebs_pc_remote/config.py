from pathlib import Path
import os

APP_NAME = "EBS PC Remote"
VERSION = "1.0.4"

DISCOVERY_PORT = 48740
CONTROL_PORT = 48741
BROADCAST_INTERVAL = 2.0
PEER_TTL = 7.0

# LAN odaklı kalite. 1080p altına düşürülmez; kaynak ekran daha küçükse doğal çözünürlük kullanılır.
MIN_STREAM_W = 1920
MIN_STREAM_H = 1080
JPEG_QUALITY = 88
TARGET_FPS = 30
MAX_PACKET = 32 * 1024 * 1024
FILE_CHUNK = 256 * 1024

def _safe_dir(*candidates):
    """
    Verilen adaylardan oluşturulabilen ilk klasörü döndürür.
    Windows'ta Documents/Downloads OneDrive'a yönlendirilmiş veya hiç oluşturulmamış olabilir.
    """
    last_error = None
    for candidate in candidates:
        if not candidate:
            continue
        try:
            p = Path(candidate).expanduser()
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception as exc:
            last_error = exc

    # Son çare: uygulamanın çalıştığı dizinin altında veri klasörü.
    fallback = Path.cwd() / "EBS_PC_Remote_Data"
    try:
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
    except Exception:
        if last_error:
            raise last_error
        raise

home = Path.home()
local_appdata = os.environ.get("LOCALAPPDATA")
userprofile = os.environ.get("USERPROFILE")

# Kimlik/ayar gibi uygulama verileri Documents'a değil LocalAppData'ya yazılır.
DATA_DIR = _safe_dir(
    Path(local_appdata) / "EBS_PC_Remote" if local_appdata else None,
    Path(userprofile) / "AppData" / "Local" / "EBS_PC_Remote" if userprofile else None,
    home / "AppData" / "Local" / "EBS_PC_Remote",
)

# Alınan dosyalar için önce gerçek kullanıcı Downloads klasörü denenir.
RECEIVE_DIR = _safe_dir(
    Path(userprofile) / "Downloads" / "EBS_PC_Remote" if userprofile else None,
    home / "Downloads" / "EBS_PC_Remote",
    DATA_DIR / "Received",
)
