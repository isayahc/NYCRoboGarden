"""Run a shared harvest mission and stream poses to a browser-rendered 3D viewer."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import threading
import time

import mujoco

from simulation.browser_scene import BrowserScene
from simulation.harvest_mission import DURATION, STOPS, HarvestMission
from simulation.garden_patrol import CROPS, build_model

DIRECTORY = Path(__file__).parent
PAGE = DIRECTORY / 'dashboard.html'
ASSETS = {
    '/': (PAGE, 'text/html; charset=utf-8'),
    '/viewer.js': (DIRECTORY / 'viewer.js', 'text/javascript; charset=utf-8'),
    '/vendor/three.module.min.js': (DIRECTORY / 'vendor/three.module.min.js', 'text/javascript'),
    '/vendor/OrbitControls.js': (DIRECTORY / 'vendor/OrbitControls.js', 'text/javascript'),
    '/vendor/BufferGeometryUtils.js': (DIRECTORY / 'vendor/BufferGeometryUtils.js', 'text/javascript'),
}


class MissionRuntime:
    """Own one mission clock; browsers render shared poses without controlling it."""

    def __init__(self, output: Path, fps: int = 30) -> None:
        if fps <= 0:
            raise ValueError('Pose update rate must be positive')
        self.output = output
        self.fps = fps
        self.lock = threading.Lock()
        self.changed = threading.Condition(self.lock)
        self.stop = threading.Event()
        self.ready = threading.Event()
        self.transforms = []
        self.scene = {}
        self.meshes = {}
        self.sequence = 0
        self.status: dict[str, object] = {'phase': 'starting'}
        self.error: Exception | None = None
        self.thread = threading.Thread(target=self.run, name='farm-mission', daemon=True)

    def snapshot(self):
        """Return an atomic pose/status pair without advancing the simulation."""
        with self.lock:
            return self.transforms, dict(self.status)

    def run(self) -> None:
        """Advance kinematics without any renderer, framebuffer or image encoder."""
        try:
            self.output.mkdir(parents=True, exist_ok=True)
            (self.output / 'mission.json').write_text('[]\n')
            model = build_model(harvest=True)
            mission = HarvestMission(model)
            data = mujoco.MjData(model)
            mission.update(data, 0)
            exported = BrowserScene(model, data)
            self.scene, self.meshes = exported.document, exported.meshes
            results: list[dict[str, object]] = []
            cycle = 0
            start = time.monotonic()
            deadline = start
            while not self.stop.is_set():
                total_elapsed = time.monotonic() - start
                current_cycle = int(total_elapsed // DURATION) + 1
                if current_cycle != cycle:
                    cycle = current_cycle
                    results = []
                    temporary = self.output / 'mission.tmp'
                    temporary.write_text('[]\n')
                    temporary.replace(self.output / 'mission.json')
                state = mission.update(data, total_elapsed % DURATION)
                for bed in state.completed:
                    if any(result['bed'] == bed for result in results):
                        continue
                    results.append({'cycle': cycle, 'bed': bed, 'crop': CROPS[bed],
                                    'task': 'pick and place in collection box',
                                    'result': 'simulated vegetable deposited', 'simulated': True})
                    temporary = self.output / 'mission.tmp'
                    temporary.write_text(json.dumps(results, indent=2) + '\n')
                    temporary.replace(self.output / 'mission.json')
                status = {**asdict(state), 'duration': DURATION, 'simulated': True,
                          'cycle': cycle, 'total_elapsed': total_elapsed, 'looping': True,
                          'focus': exported.focus(data), 'pose_hz': self.fps,
                          'active_crop': CROPS[state.active_bed] if state.active_bed is not None else None,
                          'box_count': len(state.deposited),
                          'tasks': [{'bed': bed, 'crop': CROPS[bed], 'task': 'Harvest into box',
                                     'status': 'complete' if bed in state.completed else
                                     'active' if bed == state.active_bed else 'pending'} for _, bed in STOPS],
                          'results': list(results)}
                transforms = exported.poses(data)
                with self.changed:
                    self.sequence += 1
                    status['sequence'] = self.sequence
                    self.transforms, self.status = transforms, status
                    self.changed.notify_all()
                self.ready.set()
                # Spend only the remainder of the frame budget sleeping.
                deadline += 1/self.fps
                now = time.monotonic()
                if deadline < now:
                    deadline = now
                self.stop.wait(max(0, deadline-now))
        except Exception as exc:
            self.error = exc
            with self.changed:
                self.status = {'phase': 'error', 'error': str(exc)}
                self.changed.notify_all()
            self.ready.set()


def handler_for(runtime: MissionRuntime) -> type[BaseHTTPRequestHandler]:
    """Read-only scene, pose and event routes; browser visits never restart missions."""
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = self.path.split('?', 1)[0]
            if path == '/api/events':
                self.events()
                return
            cache = 'no-store'
            if path in ASSETS:
                asset, content_type = ASSETS[path]
                payload = asset.read_bytes()
            elif path == '/api/scene':
                payload, content_type = json.dumps(runtime.scene).encode(), 'application/json'
            elif path in ('/api/status', '/api/state'):
                transforms, status = runtime.snapshot()
                if path == '/api/state':
                    status['transforms'] = transforms
                payload, content_type = json.dumps(status).encode(), 'application/json'
            elif match := re.fullmatch(r'/assets/mesh/(\d+)\.bin', path):
                payload = runtime.meshes.get(int(match[1]))
                if payload is None:
                    self.send_error(404)
                    return
                content_type, cache = 'application/octet-stream', 'public, max-age=3600'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', cache)
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def events(self):
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('X-Accel-Buffering', 'no')
            self.end_headers()
            last = -1
            try:
                while not runtime.stop.is_set():
                    with runtime.changed:
                        runtime.changed.wait_for(lambda: runtime.sequence != last or runtime.stop.is_set() or runtime.error, timeout=10)
                        if runtime.stop.is_set():
                            return
                        if runtime.error:
                            self.wfile.write(b'event: error\ndata: {"error":"Mission failed"}\n\n')
                            self.wfile.flush()
                            return
                        if runtime.sequence == last:
                            payload = b': keepalive\n\n'
                        else:
                            last = runtime.sequence
                            state = {**runtime.status, 'transforms': runtime.transforms}
                            payload = b'data: ' + json.dumps(state, separators=(',', ':')).encode() + b'\n\n'
                    self.wfile.write(payload)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, format: str, *args: object) -> None:
            pass

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--fps', type=int, default=30, help='Server pose update rate (browser renders at display refresh rate)')
    parser.add_argument('--output', type=Path, default=Path('data/generated/farm-mission'))
    args = parser.parse_args()
    if args.fps <= 0:
        parser.error('--fps must be positive')
    runtime = MissionRuntime(args.output, args.fps)
    with ThreadingHTTPServer((args.host, args.port), handler_for(runtime)) as server:
        runtime.thread.start()
        try:
            if not runtime.ready.wait(60):
                raise RuntimeError('Simulation did not start within 60 seconds')
            if runtime.error:
                raise RuntimeError('Simulation initialization failed') from runtime.error
            print(f'Farm mission running: http://{args.host}:{server.server_port} (browser 3D, {args.fps} Hz poses)', flush=True)
            server.serve_forever(poll_interval=.2)
        except KeyboardInterrupt:
            pass
        finally:
            runtime.stop.set()
            with runtime.changed:
                runtime.changed.notify_all()
            runtime.thread.join(timeout=5)


if __name__ == '__main__':
    main()
