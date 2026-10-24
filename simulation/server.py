"""Start a shared, real-time farm inspection simulation and browser dashboard."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import os
from pathlib import Path
import threading
import time

# Must be selected before importing MuJoCo. Override for other platforms.
os.environ.setdefault('MUJOCO_GL', 'egl')
import mujoco
from PIL import Image

from simulation.farm_mission import DURATION, STOPS, mission_pose
from simulation.garden_patrol import CROPS, build_model

PAGE = Path(__file__).with_name('dashboard.html')


class MissionRuntime:
    """Own one renderer and one mission; clients only read shared snapshots."""

    def __init__(self, output: Path, fps: int = 15) -> None:
        """Prepare synchronization and a destination for simulated inspection evidence."""
        self.output = output
        self.fps = fps
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.ready = threading.Event()
        self.jpeg = b''
        self.status: dict[str, object] = {'phase': 'starting'}
        self.error: Exception | None = None
        self.thread = threading.Thread(target=self.run, name='farm-mission', daemon=True)

    def snapshot(self) -> tuple[bytes, dict[str, object]]:
        """Return an atomic image/status pair without advancing the simulation."""
        with self.lock:
            return self.jpeg, dict(self.status)

    def run(self) -> None:
        """Advance from server startup, render frames and persist each completed scan."""
        try:
            self.output.mkdir(parents=True, exist_ok=True)
            (self.output / 'mission.json').write_text('[]\n')
            model = build_model()
            data = mujoco.MjData(model)
            camera = mujoco.MjvCamera()
            camera.lookat[:] = (0, 0, .15)
            camera.distance, camera.azimuth, camera.elevation = 6.5, 135, -40
            results: list[dict[str, object]] = []
            with mujoco.Renderer(model, height=540, width=960) as renderer:
                start = time.monotonic()
                while not self.stop.is_set():
                    state = mission_pose(model, data, time.monotonic()-start)
                    for bed in state.completed:
                        if any(result['bed'] == bed for result in results):
                            continue
                        results.append({'bed': bed, 'crop': CROPS[bed], 'task': 'visual inspection sweep',
                                        'result': 'simulated scan completed', 'simulated': True})
                        temporary = self.output / 'mission.tmp'
                        temporary.write_text(json.dumps(results, indent=2) + '\n')
                        temporary.replace(self.output / 'mission.json')
                    renderer.update_scene(data, camera)
                    image = Image.fromarray(renderer.render())
                    # Keep the actual mounted arm visible while retaining a farm overview.
                    close = mujoco.MjvCamera()
                    close.lookat[:] = data.xpos[model.body('arm_mount').id]
                    close.distance, close.azimuth, close.elevation = 1.35, 135, -25
                    renderer.update_scene(data, close)
                    inset = Image.fromarray(renderer.render()).resize((320, 180))
                    image.paste(inset, (630, 10))
                    buffer = BytesIO()
                    image.save(buffer, format='JPEG', quality=85)
                    status = {**asdict(state), 'duration': DURATION, 'simulated': True,
                              'active_crop': CROPS[state.active_bed] if state.active_bed is not None else None,
                              'tasks': [{'bed': bed, 'crop': CROPS[bed], 'task': 'Inspect crop',
                                         'status': 'complete' if bed in state.completed else
                                         'active' if bed == state.active_bed else 'pending'} for _, bed in STOPS],
                              'results': list(results)}
                    with self.lock:
                        self.jpeg, self.status = buffer.getvalue(), status
                    self.ready.set()
                    if state.phase == 'complete':
                        break
                    self.stop.wait(1/self.fps)
        except Exception as exc:
            self.error = exc
            with self.lock:
                self.status = {'phase': 'error', 'error': str(exc)}
            self.ready.set()


def handler_for(runtime: MissionRuntime) -> type[BaseHTTPRequestHandler]:
    """Create read-only routes; visits and refreshes never restart the robot."""
    class Handler(BaseHTTPRequestHandler):
        """Serve the dashboard, latest JPEG and mission state."""

        def do_GET(self) -> None:
            """Respond with the current snapshot or a fixed dashboard asset."""
            path = self.path.split('?', 1)[0]
            frame, status = runtime.snapshot()
            if path == '/':
                payload, content_type = PAGE.read_bytes(), 'text/html; charset=utf-8'
            elif path == '/api/status':
                payload, content_type = json.dumps(status).encode(), 'application/json'
            elif path == '/frame.jpg':
                payload, content_type = frame, 'image/jpeg'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, format: str, *args: object) -> None:
            """Suppress high-frequency frame request logging."""

    return Handler


def main() -> None:
    """Bind locally, start the mission once and shut down cleanly on Ctrl-C."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--output', type=Path, default=Path('data/generated/farm-mission'))
    args = parser.parse_args()
    runtime = MissionRuntime(args.output)
    with ThreadingHTTPServer((args.host, args.port), handler_for(runtime)) as server:
        runtime.thread.start()
        try:
            if not runtime.ready.wait(60):
                raise RuntimeError('Simulation renderer did not start within 60 seconds')
            if runtime.error:
                raise RuntimeError('Simulation initialization failed; check OpenGL/EGL drivers') from runtime.error
            print(f'Farm mission running: http://{args.host}:{server.server_port}', flush=True)
            server.serve_forever(poll_interval=.2)
        except KeyboardInterrupt:
            pass
        finally:
            runtime.stop.set()
            runtime.thread.join(timeout=5)


if __name__ == '__main__':
    main()
