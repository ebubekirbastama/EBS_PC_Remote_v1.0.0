# EBS PC Remote v1.0.4

Windows ↔ Windows, aynı LAN üzerinde çalışan ayrı EBS uzak masaüstü projesidir.

## Ana özellikler

- 9 haneli kalıcı PC ID
- LAN'daki açık EBS PC Remote bilgisayarlarını UDP discovery ile otomatik listeleme
- Karttan veya ID ile bağlantı
- Karşı tarafta modern Kabul / Reddet bağlantı isteği
- ECDH P-256 + HKDF-SHA256 + AES-256-GCM oturum şifrelemesi
- Yalnızca private/LAN IP kabulü
- Windows Firewall Private profil kurallarını otomatik ekleme
- Uzak ekran 1080p tabanlı JPEG akışı
- Tam ekran F11
- Mouse move, sol/sağ tık, çift tık, drag ve scroll
- Klavye aktarımı
- Drag & drop ile dosya aktarımı + SHA-256 doğrulama
- Sesli görüşme altyapısı
- Kamera + sesli görüntülü görüşme altyapısı
- Bağlantı kapanınca ekran/ses/kamera kaynaklarını kapatma
- Modern CustomTkinter arayüz
- PyInstaller Builder

## Çalıştırma

1. `start_builder.bat` ile Builder'ı açın.
2. `WINDOWS EXE DERLE` butonuna basın.
3. Çıktı: `dist\EBS_PC_Remote.exe`
4. İki PC'de de EXE'yi çalıştırın ve Windows UAC isteğini kabul edin.
5. Windows ağ profilinin `Private/Özel` olduğundan emin olun.
6. Aynı ağdaki PC'ler ana ekranda otomatik listelenir.

## Güvenlik yaklaşımı

Bu uygulama gizli veya unattended erişim için tasarlanmamıştır. Her yeni bağlantı karşı bilgisayarda görünür kullanıcı onayı gerektirir. Firewall kuralları yalnızca Windows `Private` profilinde açılır. LAN dışı istemciler reddedilir.

## Performans

Mevcut v1 görüntü taşıması JPEG tabanlıdır. LAN üzerinde yüksek kalite verir; ancak AnyDesk/RDP seviyesinde 60 FPS / GPU codec hedeflenirse sonraki sürümde H.264/HEVC donanım codec katmanı eklenmelidir.


## v1.0.1 Path Fix

- Windows kullanıcı profilinde `Documents` klasörü bulunmadığında oluşan `WinError 2` düzeltildi.
- Kimlik ve uygulama verileri artık öncelikle `%LOCALAPPDATA%\EBS_PC_Remote` altında tutulur.
- Alınan dosyalar önce `%USERPROFILE%\Downloads\EBS_PC_Remote` altında oluşturulur.
- Gerekli üst klasörler `parents=True` ile otomatik oluşturulur.
- Standart Windows klasörleri kullanılamazsa uygulama otomatik güvenli fallback dizinine geçer.


## v1.0.2 Tkinter / PyInstaller Fix

- `ModuleNotFoundError: No module named 'tkinter'` için Builder düzeltildi.
- Tkinter'ın pip paketi olmadığı dikkate alınarak build öncesi gerçek Python Tcl/Tk kontrolü eklendi.
- PyInstaller'a `tkinter`, `_tkinter`, `ttk`, `messagebox`, `filedialog` hidden-import'ları eklendi.
- Ana Python kurulumundaki `tcl` data klasörü ve mevcut Tcl/Tk DLL'leri EXE paketine açıkça dahil edilir.
- Python kurulumunda Tcl/Tk gerçekten yoksa Builder bozuk EXE üretmek yerine anlaşılır hata verir.


## v1.0.3 – RDP / Görüntü Kalitesi Düzeltmeleri

### Tek yönlü RDP oturumu
- Bağlantıyı başlatan PC uzak ekranı açar ve kontrol eder.
- Bağlantıyı kabul eden PC artık karşı tarafın ekranını otomatik açmaz.
- Böylece bir kullanıcı bağlandığında ters yönde otomatik ikinci uzak masaüstü oturumu oluşmaz.

### Görüntü kalitesi
- JPEG kalite seviyesi 94'e yükseltildi.
- JPEG 4:4:4 (`subsampling=0`) kullanılır; yazı ve UI kenarları daha nettir.
- Hedef FPS 20.
- 1080p ve QHD kaynak ekranlar doğal çözünürlükte gönderilir.
- Çok yüksek 4K kaynaklar CPU/LAN dengesi için en fazla 2560×1440'a ölçeklenir.
- Kaynak çözünürlük gereksiz yere upscale edilmez.

### Ekran boyutlandırma
- Uzak masaüstü viewer bağlantıda otomatik maximize edilir.
- Uzak ekranın en-boy oranı korunur.
- 24 inç / 32 inç gibi fiziksel monitör boyutu yerine gerçek kullanılabilir piksel alanına göre otomatik fit yapılır.
- F11 ile gerçek tam ekran korunur.


## v1.0.4 Low Latency

- 1920x1080 low-latency profile
- 30 FPS target
- OpenCV JPEG encode/decode
- Q88 JPEG quality
- capture and encode/send separated
- only newest frame is retained; stale frames are dropped
- receiver also renders only the newest frame
- TCP_NODELAY enabled
- 4 MB socket buffers
- mouse move throttled to 60 Hz
- status bar shows displayed FPS and dropped-frame count
