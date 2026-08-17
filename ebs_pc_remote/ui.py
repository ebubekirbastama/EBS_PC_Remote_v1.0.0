import io, os, time, threading, tkinter as tk
import cv2, numpy as np
from tkinter import messagebox, filedialog
import customtkinter as ctk
from PIL import Image, ImageTk
from .util import format_id, private_ipv4
from .network import Client

BG="#07111f"; CARD="#0d1a2d"; CARD2="#10213a"; LINE="#1c3556"; TEXT="#eef7ff"; MUTED="#8fa9c4"
CYAN="#19d4ff"; BLUE="#2678ff"; GREEN="#2cdf83"; RED="#ff5364"; PURPLE="#7c5cff"

class RemoteViewer(ctk.CTkToplevel):
    def __init__(self, master, session):
        super().__init__(master)
        self.session=session; self.title(f"EBS PC Remote • {session.peer['name']}")
        self.geometry("1280x800"); self.minsize(900,600)
        self.after(120, self._maximize)
        self.configure(fg_color="#030810")
        self.full=False; self.photo=None; self.frame_size=(1,1); self.drag=False
        self._pending_frame = None
        self._frame_lock = threading.Lock()
        self._last_move_sent = 0.0
        self._rx_frames = 0
        self._fps_mark = time.perf_counter()
        self._display_fps = 0.0
        self._build()
        self.after(16, self._render_pump)
        session.on("screen_frame", self._frame)
        session.on("camera_frame", self._camera_frame)
        session.on("call_request", self._call_request)
        session.on("call_stop", lambda m,p:self.after(0,self._stop_call_ui))
        session.on_status(lambda k,t:self.after(0,lambda:self.status.configure(text=t)))
        self.protocol("WM_DELETE_WINDOW", self.close)
        session.send("screen_start",{})

    def _build(self):
        top=ctk.CTkFrame(self,fg_color=BG,height=58,corner_radius=0); top.pack(fill="x")
        ctk.CTkLabel(top,text=f"  {self.session.peer['name']}",font=("Segoe UI",18,"bold"),text_color=TEXT).pack(side="left",padx=14,pady=12)
        self.status=ctk.CTkLabel(top,text="● AES-256 • LAN • Yüksek Kalite",text_color=GREEN,font=("Segoe UI",12,"bold"))
        self.status.pack(side="left",padx=14)
        for txt,cmd in [("Dosya Gönder",self.pick_file),("Sesli",self.audio_call),("Görüntülü",self.video_call),("Tam Ekran  F11",self.toggle_full)]:
            ctk.CTkButton(top,text=txt,command=cmd,width=115,height=34,corner_radius=10,fg_color=CARD2,hover_color=LINE).pack(side="right",padx=5,pady=10)

        self.canvas=tk.Canvas(self,bg="#02050a",highlightthickness=0,cursor="arrow")
        self.canvas.pack(fill="both",expand=True)
        self.image_item=self.canvas.create_image(0,0,anchor="nw")
        self.canvas.bind("<Configure>",lambda e:self._redraw())
        self.canvas.bind("<Motion>",self._move); self.canvas.bind("<ButtonPress-1>",self._down)
        self.canvas.bind("<ButtonRelease-1>",self._up); self.canvas.bind("<Double-Button-1>",self._double)
        self.canvas.bind("<Button-3>",self._right); self.canvas.bind("<MouseWheel>",self._wheel)
        self.bind("<KeyPress>",self._key); self.bind("<F11>",lambda e:self.toggle_full())
        self.focus_force()

        try:
            from tkinterdnd2 import DND_FILES
            self.canvas.drop_target_register(DND_FILES)
            self.canvas.dnd_bind("<<Drop>>", self._drop)
        except Exception: pass

    def _coords(self,e):
        cw=max(1,self.canvas.winfo_width()); ch=max(1,self.canvas.winfo_height())
        iw,ih=self.frame_size
        scale=min(cw/iw,ch/ih); dw,dh=iw*scale,ih*scale
        ox=(cw-dw)/2; oy=(ch-dh)/2
        if e.x<ox or e.x>ox+dw or e.y<oy or e.y>oy+dh:return None
        return ((e.x-ox)/dw,(e.y-oy)/dh)

    def _sendc(self,a,e=None,**kw):
        m={"action":a}; p=self._coords(e) if e else None
        if p:m.update(x=p[0],y=p[1])
        m.update(kw); self.session.send("control",m)

    def _move(self,e):
        if self.drag:
            return
        now = time.perf_counter()
        if now - self._last_move_sent < (1.0 / 60.0):
            return
        self._last_move_sent = now
        self._sendc("move",e)
    def _down(self,e): self.drag=True; self._sendc("down",e,button="left")
    def _up(self,e): self._sendc("up",e,button="left"); self.drag=False
    def _double(self,e): self._sendc("double",e)
    def _right(self,e): self._sendc("click",e,button="right")
    def _wheel(self,e): self._sendc("scroll",e,delta=1 if e.delta>0 else -1)
    def _key(self,e):
        k=e.keysym.lower()
        mapping={"return":"enter","escape":"esc","prior":"pageup","next":"pagedown"}
        self.session.send("control",{"action":"key","key":mapping.get(k,k)})

    def _frame(self,meta,payload):
        with self._frame_lock:
            self._pending_frame = (meta, payload)

    def _render_pump(self):
        item = None
        with self._frame_lock:
            if self._pending_frame is not None:
                item = self._pending_frame
                self._pending_frame = None

        if item is not None:
            meta, payload = item
            try:
                arr = np.frombuffer(payload, dtype=np.uint8)
                bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if bgr is not None:
                    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(rgb)
                    self.frame_size = img.size
                    self._last_img = img
                    self._rx_frames += 1

                    now = time.perf_counter()
                    elapsed = now - self._fps_mark
                    if elapsed >= 0.5:
                        self._display_fps = self._rx_frames / elapsed
                        self._rx_frames = 0
                        self._fps_mark = now

                    w = meta.get("source_w", meta.get("w", img.width))
                    h = meta.get("source_h", meta.get("h", img.height))
                    q = meta.get("quality", "")
                    dropped = meta.get("dropped", 0)
                    self.status.configure(
                        text=f"● AES-256 • LAN • {w}×{h} • Q{q} • {self._display_fps:.0f} FPS • Drop {dropped}"
                    )
                    self._redraw()
            except Exception:
                pass

        self.after(16, self._render_pump)

    def _redraw(self):
        if not hasattr(self,"_last_img"): return
        cw=max(2,self.canvas.winfo_width()); ch=max(2,self.canvas.winfo_height())
        iw,ih=self._last_img.size
        scale=min(cw/iw,ch/ih); size=(max(1,int(iw*scale)),max(1,int(ih*scale)))
        if size != self._last_img.size:
            arr = np.asarray(self._last_img)
            interp = cv2.INTER_AREA if size[0] < self._last_img.width else cv2.INTER_LINEAR
            arr = cv2.resize(arr, size, interpolation=interp)
            img = Image.fromarray(arr)
        else:
            img = self._last_img
        self.photo=ImageTk.PhotoImage(img)
        self.canvas.itemconfig(self.image_item,image=self.photo)
        self.canvas.coords(self.image_item,(cw-size[0])//2,(ch-size[1])//2)

    def _maximize(self):
        try:
            self.state("zoomed")
        except Exception:
            try:
                self.attributes("-zoomed", True)
            except Exception:
                pass

    def toggle_full(self):
        self.full=not self.full; self.attributes("-fullscreen",self.full)

    def pick_file(self):
        p=filedialog.askopenfilename()
        if p: threading.Thread(target=self.session.send_file,args=(p,),daemon=True).start()

    def _drop(self,e):
        paths=self.tk.splitlist(e.data)
        for p in paths:
            if os.path.isfile(p): threading.Thread(target=self.session.send_file,args=(p,),daemon=True).start()

    def audio_call(self):
        if messagebox.askyesno("Sesli Görüşme","Karşı bilgisayara sesli görüşme isteği gönderilsin mi?",parent=self):
            self.session.send("call_request",{"mode":"audio"})

    def video_call(self):
        if messagebox.askyesno("Görüntülü Görüşme","Karşı bilgisayara görüntülü görüşme isteği gönderilsin mi?",parent=self):
            self.session.send("call_request",{"mode":"video"})

    def _call_request(self,m,p):
        mode=m.get("mode","audio")
        def ask():
            if messagebox.askyesno("EBS PC Remote",f"{self.session.peer['name']} {'görüntülü' if mode=='video' else 'sesli'} görüşme istiyor.\n\nKabul edilsin mi?",parent=self):
                self.session.send("call_accept",{"mode":mode})
                self.session.start_audio()
                if mode=="video": self.session.start_camera(); self._show_call(mode)
            else:self.session.send("call_reject",{"mode":mode})
        self.after(0,ask)

    def _show_call(self,mode):
        if hasattr(self,"callwin") and self.callwin.winfo_exists():return
        self.callwin=ctk.CTkToplevel(self); self.callwin.title("EBS Görüşme"); self.callwin.geometry("900x620"); self.callwin.configure(fg_color=BG)
        self.callimg=ctk.CTkLabel(self.callwin,text="Kamera bekleniyor..." if mode=="video" else "Sesli görüşme aktif",text_color=TEXT,font=("Segoe UI",20,"bold"))
        self.callimg.pack(fill="both",expand=True,padx=20,pady=20)
        ctk.CTkButton(self.callwin,text="Görüşmeyi Sonlandır",fg_color=RED,command=self.end_call,height=44).pack(pady=14)

    def _camera_frame(self,m,payload):
        if not hasattr(self,"callimg"):return
        try:
            img=Image.open(io.BytesIO(payload)).convert("RGB"); img.thumbnail((820,500))
            ph=ctk.CTkImage(light_image=img,dark_image=img,size=img.size)
            self._callphoto=ph; self.after(0,lambda:self.callimg.configure(image=ph,text=""))
        except Exception:pass

    def end_call(self):
        self.session.send("call_stop",{}); self.session.stop_audio(); self.session.stop_camera(); self._stop_call_ui()

    def _stop_call_ui(self):
        self.session.stop_audio(); self.session.stop_camera()
        try:self.callwin.destroy()
        except Exception:pass

    def close(self):
        try:self.session.send("screen_stop",{})
        except Exception:pass
        self.destroy()

class MainWindow(ctk.CTk):
    def __init__(self, identity, discovery, server):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.identity=identity; self.discovery=discovery; self.server=server
        self.title("EBS PC Remote"); self.geometry("1260x780"); self.minsize(1050,680)
        self.configure(fg_color=BG)
        self.peers={}; self.sessions=[]
        self._build()
        self.after(300,self._refresh_peers)

    def _build(self):
        side=ctk.CTkFrame(self,width=220,corner_radius=0,fg_color="#081421"); side.pack(side="left",fill="y"); side.pack_propagate(False)
        ctk.CTkLabel(side,text="EBS",font=("Segoe UI",34,"bold"),text_color=CYAN).pack(anchor="w",padx=26,pady=(28,0))
        ctk.CTkLabel(side,text="PC REMOTE",font=("Segoe UI",14,"bold"),text_color=MUTED).pack(anchor="w",padx=27,pady=(0,28))
        for t in ["◉  Bağlantı","⌁  Bu Ağdaki PC'ler","▣  Oturumlar","⇄  Dosyalar","◖  Görüşmeler","⚙  Ayarlar"]:
            ctk.CTkButton(side,text=t,anchor="w",height=44,corner_radius=10,fg_color="transparent",hover_color=CARD2,text_color=TEXT,font=("Segoe UI",14,"bold")).pack(fill="x",padx=14,pady=4)
        ctk.CTkLabel(side,text="LAN ONLY\nAES-256-GCM",text_color=GREEN,font=("Consolas",11,"bold")).pack(side="bottom",pady=24)

        self.main=ctk.CTkScrollableFrame(self,fg_color=BG,corner_radius=0); self.main.pack(side="left",fill="both",expand=True)
        ctk.CTkLabel(self.main,text="Bağlantı",font=("Segoe UI",30,"bold"),text_color=TEXT).pack(anchor="w",padx=30,pady=(26,2))
        ctk.CTkLabel(self.main,text="Aynı ağdaki Windows bilgisayarlarına güvenli uzaktan erişim",font=("Segoe UI",13),text_color=MUTED).pack(anchor="w",padx=31,pady=(0,22))

        row=ctk.CTkFrame(self.main,fg_color="transparent"); row.pack(fill="x",padx=28)
        mine=ctk.CTkFrame(row,fg_color=CARD,corner_radius=20,border_width=1,border_color=LINE); mine.pack(side="left",fill="both",expand=True,padx=(0,8))
        ctk.CTkLabel(mine,text="BU BİLGİSAYAR",font=("Segoe UI",12,"bold"),text_color=CYAN).pack(anchor="w",padx=24,pady=(20,4))
        ctk.CTkLabel(mine,text=format_id(self.identity["id"]),font=("Consolas",36,"bold"),text_color=TEXT).pack(anchor="w",padx=24)
        ctk.CTkLabel(mine,text=f"{self.identity['name']}  •  {private_ipv4()}",font=("Segoe UI",13),text_color=MUTED).pack(anchor="w",padx=24,pady=(4,20))

        conn=ctk.CTkFrame(row,fg_color=CARD,corner_radius=20,border_width=1,border_color=LINE); conn.pack(side="left",fill="both",expand=True,padx=(8,0))
        ctk.CTkLabel(conn,text="ID İLE BAĞLAN",font=("Segoe UI",12,"bold"),text_color=CYAN).pack(anchor="w",padx=24,pady=(20,7))
        self.id_entry=ctk.CTkEntry(conn,placeholder_text="9 haneli PC ID",height=44,corner_radius=12,border_color=LINE,fg_color=CARD2,font=("Consolas",18))
        self.id_entry.pack(fill="x",padx=24)
        ctk.CTkButton(conn,text="BAĞLAN",height=44,corner_radius=12,fg_color=BLUE,hover_color="#195cd0",font=("Segoe UI",14,"bold"),command=self.connect_id).pack(fill="x",padx=24,pady=(12,20))

        ctk.CTkLabel(self.main,text="Bu Ağdaki PC'ler",font=("Segoe UI",21,"bold"),text_color=TEXT).pack(anchor="w",padx=30,pady=(30,10))
        self.peerbox=ctk.CTkFrame(self.main,fg_color="transparent"); self.peerbox.pack(fill="x",padx=28)
        self.empty=ctk.CTkLabel(self.peerbox,text="Ağda EBS PC Remote çalıştıran başka bilgisayar aranıyor…",text_color=MUTED,font=("Segoe UI",13))
        self.empty.pack(anchor="w",pady=16)

        self.log=ctk.CTkTextbox(self.main,height=130,corner_radius=15,fg_color="#040b13",border_width=1,border_color=LINE,text_color="#8ce9b1",font=("Consolas",11))
        self.log.pack(fill="x",padx=28,pady=28); self._log("EBS PC Remote hazır. LAN keşfi aktif.")

    def _log(self,t):
        self.log.insert("end",f"[{time.strftime('%H:%M:%S')}] {t}\n"); self.log.see("end")

    def update_peers(self,peers):
        self.peers=peers

    def _refresh_peers(self):
        for w in self.peerbox.winfo_children(): w.destroy()
        if not self.peers:
            ctk.CTkLabel(self.peerbox,text="Ağda EBS PC Remote çalıştıran başka bilgisayar aranıyor…",text_color=MUTED).pack(anchor="w",pady=16)
        else:
            for pid,p in sorted(self.peers.items(), key=lambda x:x[1].get("name","")):
                f=ctk.CTkFrame(self.peerbox,fg_color=CARD,corner_radius=16,border_width=1,border_color=LINE)
                f.pack(fill="x",pady=6)
                ctk.CTkLabel(f,text="●",text_color=GREEN,font=("Segoe UI",16,"bold")).pack(side="left",padx=(18,8),pady=15)
                ctk.CTkLabel(f,text=p.get("name","PC"),text_color=TEXT,font=("Segoe UI",15,"bold")).pack(side="left")
                ctk.CTkLabel(f,text=f"  {format_id(pid)}  •  {p.get('ip')}",text_color=MUTED,font=("Consolas",12)).pack(side="left",padx=12)
                ctk.CTkButton(f,text="Bağlan",width=100,height=34,corner_radius=10,fg_color=BLUE,command=lambda pp=p:self.connect_peer(pp)).pack(side="right",padx=14,pady=10)
        self.after(1000,self._refresh_peers)

    def connect_id(self):
        pid="".join(c for c in self.id_entry.get() if c.isdigit())
        p=self.peers.get(pid)
        if not p:
            messagebox.showwarning("EBS PC Remote","Bu ID şu anda yerel ağda görünmüyor.\nKarşı PC'de EBS PC Remote açık olmalı.",parent=self); return
        self.connect_peer(p)

    def connect_peer(self,p):
        def work():
            try:
                self.after(0,lambda:self._log(f"{p['name']} bağlantısı başlatılıyor…"))
                s=Client.connect(self.identity,p); self._register_session(s)
                self.after(0,lambda:RemoteViewer(self,s))
            except Exception as e:self.after(0,lambda:messagebox.showerror("Bağlantı Hatası",str(e),parent=self))
        threading.Thread(target=work,daemon=True).start()

    def incoming(self,s):
        self.after(0,lambda:self._incoming_ui(s))

    def _incoming_ui(self,s):
        # RDP mantığı: bağlantıyı kabul eden PC karşı tarafın ekranını otomatik açmaz.
        # Yalnızca bağlantıyı başlatan kullanıcı viewer görür/kontrol eder.
        self._register_session(s)
        self._log(f"{s.peer['name']} bağlandı. Bu bilgisayarın ekranı paylaşılıyor.")

    def _register_session(self,s):
        self.sessions.append(s); self._wire_call(s)
        s.on("screen_start",lambda m,p:s.start_screen())
        s.on("screen_stop",lambda m,p:s.stop_screen())
        s.on("call_accept",lambda m,p:self.after(0,lambda:self._call_accepted(s,m)))
        s.on("call_reject",lambda m,p:self.after(0,lambda:messagebox.showinfo("Görüşme","Karşı taraf görüşmeyi reddetti.",parent=self)))
        s.on("call_stop",lambda m,p:(s.stop_audio(),s.stop_camera()))
        s.on_status(lambda k,t:self.after(0,lambda:self._log(f"{s.peer['name']}: {t}")))

    def _wire_call(self,s): pass
    def _call_accepted(self,s,m):
        s.start_audio()
        if m.get("mode")=="video": s.start_camera()
        self._log(f"{s.peer['name']} ile {m.get('mode')} görüşmesi başladı.")

    def modern_accept(self,peer):
        result={"v":False}; ev=threading.Event()
        def show():
            win=ctk.CTkToplevel(self); win.title("EBS PC Remote • Bağlantı İsteği"); win.geometry("520x390"); win.resizable(False,False); win.configure(fg_color=BG); win.grab_set()
            ctk.CTkLabel(win,text="EBS",font=("Segoe UI",36,"bold"),text_color=CYAN).pack(pady=(28,0))
            ctk.CTkLabel(win,text="Güvenli Bağlantı İsteği",font=("Segoe UI",23,"bold"),text_color=TEXT).pack(pady=(8,4))
            ctk.CTkLabel(win,text=f"{peer['name']}\n{peer['ip']}\nID  {format_id(peer['id'])}",font=("Segoe UI",15),text_color=MUTED,justify="center").pack(pady=16)
            ctk.CTkLabel(win,text="● LAN     ● AES-256-GCM",font=("Segoe UI",13,"bold"),text_color=GREEN).pack(pady=4)
            b=ctk.CTkFrame(win,fg_color="transparent"); b.pack(fill="x",padx=36,pady=24)
            def done(v):result["v"]=v; ev.set(); win.destroy()
            ctk.CTkButton(b,text="REDDET",fg_color=CARD2,hover_color=LINE,height=46,command=lambda:done(False)).pack(side="left",fill="x",expand=True,padx=(0,8))
            ctk.CTkButton(b,text="KABUL ET",fg_color=BLUE,height=46,command=lambda:done(True)).pack(side="left",fill="x",expand=True,padx=(8,0))
            win.protocol("WM_DELETE_WINDOW",lambda:done(False))
        self.after(0,show); ev.wait(); return result["v"]
