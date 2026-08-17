# EBS PC Remote v1.0.0

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Platform-Windows-0078D4?style=for-the-badge&logo=windows&logoColor=white)
![LAN](https://img.shields.io/badge/Network-LAN-0A66C2?style=for-the-badge)
![Encryption](https://img.shields.io/badge/Channel-AES--GCM%20%2B%20ECDH-8A2BE2?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-v1.0.0-blue?style=for-the-badge)

> Windows to Windows LAN üzerinde uzak masaüstü, klavye/fare kontrolü, dosya aktarımı, ses ve kamera akışını sağlayan Python tabanlı bir PC Remote uygulaması.

## Proje Hakkında

**EBS PC Remote** aynı yerel ağ üzerindeki Windows bilgisayarların birbirini keşfetmesini ve kullanıcı onayı sonrasında uzaktan bağlantı kurmasını amaçlar.

Uygulama; peer discovery, TCP kontrol bağlantısı, şifreli veri kanalı, ekran aktarımı, mouse/keyboard kontrolü, dosya transferi, ses ve kamera akışı gibi bileşenleri ayrı modüller halinde içerir. Ana giriş noktası Windows'ta yönetici yetkisini kontrol eder, firewall kurallarını hazırlar, kimlik bilgisini yükler, TCP sunucusunu ve LAN discovery servislerini başlatır.

## Özellikler

### Uzak Masaüstü

- LAN üzerindeki bilgisayarları otomatik keşfetme
- Uzak bilgisayarın ekranını JPEG kareleri halinde aktarma
- 1080p'ye kadar ekran frame sınırı
- Ayarlanabilir hedef FPS ve JPEG kalitesi
- Ekran aktarımı için ayrı capture ve encode thread'leri

Ekran yakalama `mss`, görüntü işleme ve encoding ise OpenCV ve NumPy ile gerçekleştirilir. Frame kuyruğu tek elemanlı tutularak eski karelerin birikmesi engellenir.

### Klavye ve Fare Kontrolü

Remote session içerisinde `pyautogui` kullanılarak:

- Mouse hareketi
- Sol/sağ mouse click
- Double click
- Mouse down/up
- Scroll
- Tek tuş gönderimi
- Hotkey gönderimi
- Metin yazma

işlemleri uygulanabilir. Koordinatlar uzak ekranın normalize edilmiş değerlerinden yerel ekran çözünürlüğüne dönüştürülür.

### Dosya Transferi

Dosya aktarımında:

1. Dosya adı ve boyutu gönderilir.
2. SHA-256 hash'i gönderilir.
3. Dosya parçalara ayrılarak aktarılır.
4. Alıcı dosyayı kaydeder.
5. Transfer sonunda SHA-256 karşılaştırması yapılır.
6. Hash uyuşmazlığı durumunda transfer başarısız kabul edilir.

Aynı isimli dosyalar üzerine yazılmak yerine `_1`, `_2` gibi isimlerle yeni dosya oluşturulur.

### Ses

`sounddevice` üzerinden 16 kHz, mono, 16-bit raw audio stream kullanılır. Ses paketleri güvenli session kanalı üzerinden `audio_chunk` mesajlarıyla taşınır.

### Kamera

OpenCV ile varsayılan kamera açılır ve görüntü:

- 960x540 boyutuna ölçeklenir
- JPEG kalite 80 ile encode edilir
- `camera_frame` mesajı olarak gönderilir

Kamera akışı sonlandırıldığında kamera kaynağı serbest bırakılır.

## Güvenlik Mimarisi

Projenin önemli taraflarından biri LAN sınırlandırması ve şifreli session kanalının birlikte kullanılmasıdır.

### ECDH + HKDF

Bağlantı kurulurken taraflar **SECP256R1 ECDH** anahtar çifti oluşturur. Ortak secret üzerinden SHA-256 kullanan HKDF ile 32 byte session key türetilir.

### AES-GCM

Session içerisindeki veri `AESGCM` ile şifrelenir. Paketlerde nonce ve artan counter kullanılır; alınan counter önceki değerden küçük veya eşitse replay paketi reddedilir. Ayrıca paket boyutu için üst sınır uygulanır.

### LAN Sınırı

Discovery yalnızca private IPv4 adreslerini kabul eder. TCP sunucusu da bağlantının kaynak IP'sini private IPv4 olarak doğrular ve LAN dışındaki istemcileri reddeder.

> Bu mekanizmalar uygulamanın güvenlik tasarımını güçlendirir ancak tek başına kurumsal güvenlik değerlendirmesi veya bağımsız penetration test yerine geçmez.

## Peer Discovery

Bilgisayarlar UDP broadcast üzerinden `EBS_PC_REMOTE` magic değeriyle duyuru yayınlar.

Discovery paketinde:

- Version
- Peer ID
- Bilgisayar adı
- Private IP
- Control port

bilgileri bulunur. Peer'ler belirli bir TTL sonrasında otomatik olarak listeden temizlenir.

## Ağ Mimarisi

```text
                 EBS PC Remote LAN
                         |
          +--------------+--------------+
          |                             |
       PC A                           PC B
          |                             |
    UDP Discovery                 UDP Discovery
          |                             |
          +------------+----------------+
                       |
                 TCP Control
                       |
                 Accept / Reject
                       |
                ECDH + HKDF Key
                       |
                    AES-GCM
                       |
        +--------------+--------------+
        |              |              |
     Screen        Control       File/Media
     Frames         Input          Transfer
```

TCP sunucusu bağlantıyı kabul eder, peer onayından sonra ECDH anahtar değişimi gerçekleştirir ve `RemoteSession` oluşturur.

## Teknoloji Kartları

| Teknoloji | Kullanım |
|---|---|
| **Python** | Ana programlama dili |
| **CustomTkinter** | Modern masaüstü arayüzü |
| **mss** | Ekran yakalama |
| **OpenCV** | Kamera ve JPEG görüntü işleme |
| **NumPy** | Görüntü/frame işlemleri |
| **PyAutoGUI** | Mouse/keyboard kontrolü |
| **SoundDevice** | Ses capture/playback |
| **cryptography** | ECDH, HKDF, AES-GCM |
| **PyInstaller** | Windows EXE oluşturma |
| **qrcode[pil]** | QR kod desteği için bağımlılık |
| **Pyperclip** | Clipboard işlemleri |
| **tkinterdnd2** | Drag & drop desteği |

## Proje Yapısı

```text
EBS_PC_Remote_v1.0.0/
├── main.py                  # Uygulama giriş noktası
├── builder.py               # Windows EXE builder
├── requirements.txt
├── start_app.bat
├── start_builder.bat
├── assets/
│   └── ebs_pc_remote.ico
├── ebs_pc_remote/
│   ├── config.py
│   ├── crypto_channel.py    # ECDH/HKDF/AES-GCM kanalı
│   ├── discovery.py         # LAN peer discovery
│   ├── firewall.py          # Windows Firewall yönetimi
│   ├── media.py             # Screen streaming
│   ├── network.py           # TCP server/client
│   ├── session.py           # Remote session / file / media
│   ├── ui.py                # Kullanıcı arayüzü
│   └── util.py
└── README.md
```

## Kurulum

Windows üzerinde Python 3.x kurulu olmalıdır.

```bash
git clone https://github.com/ebubekirbastama/EBS_PC_Remote_v1.0.0.git
cd EBS_PC_Remote_v1.0.0
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Ardından:

```bash
python main.py
```

Repository'de ayrıca `start_app.bat` ve builder için `start_builder.bat` dosyaları bulunur.

## Windows EXE Oluşturma

Repository kendi GUI tabanlı builder'ını içerir.

```bash
python builder.py
```

Builder:

- İzole `.build_venv` oluşturur
- pip/setuptools/wheel günceller
- `requirements.txt` kurar
- PyInstaller kurar
- Tkinter/Tcl-Tk kontrolü yapar
- `--onefile` ve `--windowed` kullanır
- `--uac-admin` ile administrator manifest ekler
- `customtkinter` ve `tkinterdnd2` içeriklerini toplar
- mevcut `assets/ebs_pc_remote.ico` varsa EXE ikonunu kullanır
- sonucu `dist/EBS_PC_Remote.exe` olarak üretir

## Windows Firewall

Uygulama Windows'ta administrator olarak çalıştırılmaya çalışılır. Başlangıçta firewall hazırlığı yapılır.

Private profile üzerinde:

- TCP control portu için inbound allow rule
- UDP discovery portu için inbound allow rule

oluşturulur. Kurallar `netsh advfirewall` üzerinden eklenir ve önce aynı isimdeki eski kurallar silinir.

## Güvenlik ve Yetkili Kullanım

Bu yazılım uzaktaki bilgisayarda **klavye/fare kontrolü, ekran görüntüsü, dosya transferi, ses ve kamera erişimi** sağlayabildiği için yüksek ayrıcalıklı bir araçtır.

**Yalnızca sahibi olduğunuz veya açıkça yönetme yetkiniz bulunan bilgisayarlarda kullanın.**

Özellikle:

- Peer bağlantısını kabul etmeden önce bilgisayar adını ve IP'yi doğrulayın.
- Firewall kurallarının yalnızca gerekli Private profile'da açıldığını kontrol edin.
- İnternet/WAN üzerinden port yönlendirmesi yapmayın.
- EXE'yi güvenilmeyen kişilerle dağıtmayın.
- Kaynak kodunda kimlik doğrulama/authorization katmanını genişletmeden kurumsal uzaktan erişim çözümü olarak kullanmayın.

## Bilinen Teknik Sınırlamalar

- Discovery ve bağlantı private IPv4/LAN odaklıdır.
- TCP bağlantısı kurulmadan önce kullanıcı onayı mekanizması vardır.
- Uygulama yönetici yetkisi ister ve firewall kuralı oluşturur.
- Dosya transferinde SHA-256 bütünlük kontrolü bulunur; ancak dosya aktarımı için ayrı bir güven/authorization politikası tanımlanmamıştır.
- Remote input doğrudan `pyautogui` üzerinden uygulanır.
- Kamera varsayılan `VideoCapture(0)` cihazını kullanır.
- Ses 16 kHz mono raw stream olarak işlenir.
- Session protokolü özel bir uygulama protokolüdür; standart RDP/VNC değildir.

## Gelecek Geliştirmeler

- Güçlü kullanıcı/cihaz kimlik doğrulaması
- Pairing / trust store
- Sertifika tabanlı cihaz doğrulama
- Session izinleri: ekran / input / dosya / kamera / ses ayrı ayrı
- Kullanıcı onaylarının her bağlantıda açık şekilde gösterilmesi
- Transfer sırasında yeniden başlatma/resume desteği
- Daha gelişmiş congestion/backpressure yönetimi
- UDP discovery yerine isteğe bağlı manuel peer ekleme
- IPv6 desteği
- Audit log
- Connection timeout / heartbeat / keepalive
- Otomatik güncelleme mekanizması
- Test suite ve protocol integration tests

## Lisans

Repository'deki `LICENSE` dosyasına bakınız.

## Geliştirici

**Ebubekir Bastama**  
GitHub: https://github.com/ebubekirbastama

---

**EBS PC Remote v1.0.0** - Windows LAN remote desktop / remote assistance araştırma ve geliştirme projesi.
