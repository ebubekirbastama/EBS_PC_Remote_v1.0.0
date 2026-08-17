import os, time, json, threading
from pathlib import Path
from .config import RECEIVE_DIR, FILE_CHUNK
from .util import sha256_file

class RemoteSession:
    def __init__(self, channel, peer, incoming=False):
        self.channel = channel
        self.peer = peer
        self.incoming = incoming
        self.alive = True
        self.handlers = {}
        self.status_handlers = []
        self.pending_files = {}
        self.screen_streamer = None
        self.audio_running = False
        self.camera_running = False
        self._audio_in = None
        self._audio_out = None
        self._cam = None
        threading.Thread(target=self._rx, daemon=True).start()

    def on(self, kind, fn): self.handlers.setdefault(kind, []).append(fn)
    def on_status(self, fn): self.status_handlers.append(fn)
    def emit_status(self, kind, text):
        for fn in list(self.status_handlers):
            try: fn(kind, text)
            except Exception: pass

    def send(self, kind, meta=None, payload=b""):
        if self.alive: self.channel.send(kind, meta or {}, payload)

    def _rx(self):
        try:
            while self.alive:
                kind, meta, payload = self.channel.recv()
                if kind == "control": self._apply_control(meta)
                elif kind == "file_offer": self._file_offer(meta)
                elif kind == "file_chunk": self._file_chunk(meta, payload)
                elif kind == "file_done": self._file_done(meta)
                elif kind == "audio_chunk": self._audio_play(payload)
                else:
                    for fn in list(self.handlers.get(kind, [])):
                        try: fn(meta, payload)
                        except Exception as e: self.emit_status("handler_error", f"{kind}: {e}")
        except Exception as e:
            self.emit_status("closed", str(e))
        finally:
            self.close(False)

    def _apply_control(self, m):
        import pyautogui
        try:
            sw, sh = pyautogui.size()
            action = m.get("action")
            x = max(0, min(sw-1, int(float(m.get("x",0))*sw)))
            y = max(0, min(sh-1, int(float(m.get("y",0))*sh)))
            if action == "move": pyautogui.moveTo(x,y,_pause=False)
            elif action == "click": pyautogui.click(x,y,button=m.get("button","left"),_pause=False)
            elif action == "double": pyautogui.doubleClick(x,y,interval=0.12,_pause=False)
            elif action == "down": pyautogui.mouseDown(x,y,button=m.get("button","left"),_pause=False)
            elif action == "up": pyautogui.mouseUp(x,y,button=m.get("button","left"),_pause=False)
            elif action == "scroll": pyautogui.moveTo(x,y,_pause=False); pyautogui.scroll(int(m.get("delta",0)))
            elif action == "key": pyautogui.press(m.get("key",""))
            elif action == "hotkey": pyautogui.hotkey(*m.get("keys",[]))
            elif action == "text": pyautogui.write(m.get("text",""), interval=0.01)
        except Exception as e:
            self.send("control_result", {"ok":False,"error":str(e)})

    def start_screen(self):
        if self.screen_streamer is None:
            from .media import ScreenStreamer
            self.screen_streamer = ScreenStreamer(self)
        self.screen_streamer.start()

    def stop_screen(self):
        if self.screen_streamer: self.screen_streamer.stop()

    def send_file(self, path):
        p = Path(path)
        if not p.is_file(): return
        transfer = f"{int(time.time()*1000)}-{os.getpid()}"
        meta = {"id":transfer,"name":p.name,"size":p.stat().st_size,"sha256":sha256_file(p)}
        self.send("file_offer", meta)
        with p.open("rb") as f:
            seq=0
            while True:
                data=f.read(FILE_CHUNK)
                if not data: break
                self.send("file_chunk", {"id":transfer,"seq":seq}, data); seq+=1
        self.send("file_done", {"id":transfer})
        self.emit_status("file_sent", p.name)

    def _file_offer(self, m):
        safe = Path(m["name"]).name
        dst = RECEIVE_DIR / safe
        n=1
        while dst.exists():
            dst = RECEIVE_DIR / f"{dst.stem}_{n}{dst.suffix}"; n+=1
        f = dst.open("wb")
        self.pending_files[m["id"]] = {"file":f,"path":dst,"meta":m}
        self.emit_status("file_receiving", safe)

    def _file_chunk(self, m, payload):
        st=self.pending_files.get(m["id"])
        if st: st["file"].write(payload)

    def _file_done(self, m):
        st=self.pending_files.pop(m["id"],None)
        if not st: return
        st["file"].close()
        ok = sha256_file(st["path"]) == st["meta"]["sha256"]
        self.emit_status("file_received", f"{st['path'].name} ({'doğrulandı' if ok else 'HASH HATASI'})")

    def start_audio(self):
        if self.audio_running: return
        import sounddevice as sd
        self.audio_running=True
        self._audio_out = sd.RawOutputStream(samplerate=16000, channels=1, dtype="int16", blocksize=640)
        self._audio_out.start()
        def cb(indata, frames, time_info, status):
            if self.audio_running and self.alive:
                try: self.send("audio_chunk", {"rate":16000}, bytes(indata))
                except Exception: pass
        self._audio_in = sd.RawInputStream(samplerate=16000, channels=1, dtype="int16", blocksize=640, callback=cb)
        self._audio_in.start()

    def _audio_play(self, payload):
        try:
            if self.audio_running and self._audio_out: self._audio_out.write(payload)
        except Exception: pass

    def stop_audio(self):
        self.audio_running=False
        for s in (self._audio_in,self._audio_out):
            try:
                if s: s.stop(); s.close()
            except Exception: pass
        self._audio_in=self._audio_out=None

    def start_camera(self):
        if self.camera_running: return
        import cv2
        self.camera_running=True
        self._cam=cv2.VideoCapture(0)
        def loop():
            while self.camera_running and self.alive:
                ok, frame = self._cam.read()
                if not ok: break
                frame=cv2.resize(frame,(960,540))
                ok, enc=cv2.imencode(".jpg",frame,[int(cv2.IMWRITE_JPEG_QUALITY),80])
                if ok: self.send("camera_frame",{"w":960,"h":540},enc.tobytes())
                time.sleep(0.08)
        threading.Thread(target=loop,daemon=True).start()

    def stop_camera(self):
        self.camera_running=False
        try:
            if self._cam: self._cam.release()
        except Exception: pass
        self._cam=None

    def close(self, notify=True):
        if not self.alive: return
        self.alive=False
        try:
            if notify: self.send("session_close",{})
        except Exception: pass
        self.stop_screen(); self.stop_audio(); self.stop_camera()
        try:self.channel.sock.shutdown(2)
        except Exception:pass
        try:self.channel.sock.close()
        except Exception:pass
