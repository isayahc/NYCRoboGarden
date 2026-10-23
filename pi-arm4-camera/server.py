#!/usr/bin/env python3
"""Dual-camera loopback viewer; reach it through `viam machine part tunnel`."""
import argparse
import atexit
import signal
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--device', default='/dev/v4l/by-id/usb-EMEET_EMEET_SmartCam_C950_4K_A250607000704027-video-index0')
parser.add_argument('--port', type=int, default=8766)
args = parser.parse_args()
class Camera:
    def __init__(self, device, format, size, rate):
        self.condition = threading.Condition()
        self.frame = None
        self.updated = 0.0
        self.process = subprocess.Popen([
            'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'warning',
            '-f', 'v4l2', '-input_format', format, '-framerate', rate,
            '-video_size', size, '-i', device,
            '-vf', 'fps=10', '-q:v', '6', '-f', 'image2pipe', '-vcodec', 'mjpeg', 'pipe:1',
        ], stdout=subprocess.PIPE)
        atexit.register(self.process.terminate)
        threading.Thread(target=self.capture, daemon=True).start()

    def capture(self):
        buffer = b''
        while chunk := self.process.stdout.read1(65536):
            buffer += chunk
            while True:
                start = buffer.find(b'\xff\xd8')
                end = buffer.find(b'\xff\xd9', max(start, 0))
                if start < 0 or end < 0:
                    break
                with self.condition:
                    self.frame = buffer[start:end + 2]
                    self.updated = time.monotonic()
                    self.condition.notify_all()
                buffer = buffer[end + 2:]
            if len(buffer) > 10_000_000:
                buffer = b''


cameras = {
    'emeet': Camera(args.device, 'mjpeg', '1280x720', '30'),
    'icspring': Camera('/dev/v4l/by-id/usb-icSpring_icspring_camera-video-index0', 'yuyv422', '640x480', '10'),
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/':
            payload = Path(__file__).with_name('index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        parts = path.strip('/').split('/')
        key, resource = parts if len(parts) == 2 else ('emeet', parts[0])
        camera = cameras.get(key)
        if camera is None or resource not in ('stream.mjpg', 'snapshot.jpg'):
            self.send_error(404)
            return
        with camera.condition:
            ready = camera.condition.wait_for(lambda: camera.frame is not None and time.monotonic() - camera.updated < 5, timeout=5)
            image = camera.frame
        if not ready:
            self.send_error(503, 'Camera unavailable; check camera.log on the Pi')
            return
        self.send_response(200)
        self.send_header('Cache-Control', 'no-store')
        if resource == 'snapshot.jpg':
            self.send_header('Content-Type', 'image/jpeg')
            self.send_header('Content-Length', str(len(image)))
            self.end_headers()
            self.wfile.write(image)
            return
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
        self.end_headers()
        last = 0
        try:
            while True:
                with camera.condition:
                    if not camera.condition.wait_for(lambda: camera.updated > last, timeout=10):
                        return
                    image, last = camera.frame, camera.updated
                self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(image)).encode() + b'\r\n\r\n' + image + b'\r\n')
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


def terminate(signum, frame):
    raise SystemExit(0)


signal.signal(signal.SIGTERM, terminate)
server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
try:
    server.serve_forever()
finally:
    server.server_close()
    for camera in cameras.values():
        camera.process.terminate()
        camera.process.wait(timeout=5)
