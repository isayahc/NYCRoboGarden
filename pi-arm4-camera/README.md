# pi-arm4 camera viewer

Open **http://localhost:8766** while the tunnel is running.

Both cameras appear side by side: EMEET at 1280×720 and icSpring at 640×480,
each streamed as MJPEG at 10 fps.
The Python server runs on the Pi and listens only on loopback. Access uses
the Viam CLI's authenticated tunnel; no camera credentials are embedded here.

## Prerequisites

Run local commands from the repository root. Install and authenticate the Viam
CLI on your computer (`viam login`) with access to pi-arm4. The Pi needs Python 3,
FFmpeg and access to both configured `/dev/v4l/by-id/` camera devices. Camera
capture does not require the Python Viam SDK on the Pi.

For arm/gripper connectivity and read-only diagnostics, use the companion
[`viam_integration` CLI](../README.md#viam). Its `.env` API credentials and the
Viam CLI login used for this tunnel are separate authentication paths.

## Reconnect from this computer

```bash
bash pi-arm4-camera/tunnel.sh
```

## Pi files and process

The files are copied to `/tmp/pi-arm4-camera`. The server is started with:

```bash
nohup python3 /tmp/pi-arm4-camera/server.py > /tmp/pi-arm4-camera/camera.log 2>&1 < /dev/null &
```

Run that command on the Pi through `viam machine part shell --part
5302b0c9-424d-4220-85bd-08108220e07f` if the server stops. Run it only once.
This temporary server does not restart automatically after a Pi reboot.
To reinstall files after a reboot:

```bash
viam machine part cp --part 5302b0c9-424d-4220-85bd-08108220e07f -r pi-arm4-camera machine:/tmp/
```

`/emeet/snapshot.jpg` and `/icspring/snapshot.jpg` provide current JPEGs.
`/emeet/stream.mjpg` and `/icspring/stream.mjpg` provide the video streams.
The original `/snapshot.jpg` and `/stream.mjpg` URLs still select the EMEET.
The camera must not simultaneously be opened by another capture application.
