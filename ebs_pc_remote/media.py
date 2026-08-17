import time, threading, queue
import numpy as np
import cv2
from .config import TARGET_FPS, JPEG_QUALITY

MAX_STREAM_W = 1920
MAX_STREAM_H = 1080

def _fit_1080(frame):
    h, w = frame.shape[:2]
    scale = min(1.0, MAX_STREAM_W / max(1, w), MAX_STREAM_H / max(1, h))
    if scale < 1.0:
        nw = max(1, int(w * scale))
        nh = max(1, int(h * scale))
        frame = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
    return frame

class ScreenStreamer:
    def __init__(self, session):
        self.session = session
        self.running = False
        self.monitor = 1
        self.frames = queue.Queue(maxsize=1)
        self.captured = 0
        self.sent = 0
        self.dropped = 0

    def start(self):
        if self.running:
            return
        self.running = True
        threading.Thread(target=self._capture_loop, daemon=True).start()
        threading.Thread(target=self._encode_loop, daemon=True).start()

    def stop(self):
        self.running = False

    def _capture_loop(self):
        from mss import MSS
        interval = 1.0 / max(1, TARGET_FPS)
        with MSS() as sct:
            while self.running and self.session.alive:
                t = time.perf_counter()
                try:
                    mons = sct.monitors
                    idx = min(max(1, self.monitor), len(mons) - 1)
                    shot = sct.grab(mons[idx])
                    frame = np.asarray(shot, dtype=np.uint8)[:, :, :3]
                    frame = _fit_1080(frame)
                    item = (frame.copy(), shot.width, shot.height, time.perf_counter_ns())
                    try:
                        self.frames.put_nowait(item)
                    except queue.Full:
                        try:
                            self.frames.get_nowait()
                        except queue.Empty:
                            pass
                        self.dropped += 1
                        try:
                            self.frames.put_nowait(item)
                        except queue.Full:
                            pass
                    self.captured += 1
                except Exception as e:
                    self.session.emit_status("screen_error", str(e))
                    break
                remain = interval - (time.perf_counter() - t)
                if remain > 0:
                    time.sleep(remain)

    def _encode_loop(self):
        params = [int(cv2.IMWRITE_JPEG_QUALITY), int(JPEG_QUALITY)]
        while self.running and self.session.alive:
            try:
                frame, source_w, source_h, captured_ns = self.frames.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                ok, enc = cv2.imencode(".jpg", frame, params)
                if not ok:
                    continue
                h, w = frame.shape[:2]
                self.session.send(
                    "screen_frame",
                    {
                        "w": int(w),
                        "h": int(h),
                        "source_w": int(source_w),
                        "source_h": int(source_h),
                        "quality": JPEG_QUALITY,
                        "fps": TARGET_FPS,
                        "captured_ns": int(captured_ns),
                        "dropped": int(self.dropped),
                    },
                    enc.tobytes(),
                )
                self.sent += 1
            except Exception as e:
                self.session.emit_status("screen_error", str(e))
                break
