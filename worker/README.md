# JARVIS Sandbox Worker

The worker is the execution bridge for the Android app. It can run on the same Android device through Termux, on a PC, or on a trusted server.

## Termux (same Android device)
```bash
pkg update -y
pkg install python -y
cd ~/storage/downloads/JarvisSandbox/worker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export JARVIS_HOST=127.0.0.1
uvicorn jarvis_worker.main:app --host 127.0.0.1 --port 8765
```
Then in the Android app, open 3D Lab and test `http://127.0.0.1:8765`.

If Termux shared-storage virtualenv is problematic, copy the repository into `$HOME/JarvisSandbox` and run it there.

## PC / LAN worker
Do not expose the worker to a network without an access token:
```bash
export JARVIS_HOST=0.0.0.0
export JARVIS_ACCESS_TOKEN='use-a-long-random-token'
uvicorn jarvis_worker.main:app --host 0.0.0.0 --port 8765
```
Use the PC's LAN URL in the Android app. Enter the same token in the Android 3D Lab Worker access token field. Keep the service on a trusted LAN and do not port-forward it to the public internet. Do not port-forward this service to the public internet.

## Image-to-3D provider contract
The worker accepts image uploads at `POST /api/v1/3d/jobs`. To perform actual 3D inference, configure `JARVIS_3D_PROVIDER_URL` and optionally `JARVIS_3D_PROVIDER_TOKEN`.

The configured provider must implement:
- `POST {base}/jobs` as multipart with `image` and form fields `prompt`, `output_format=glb`; return JSON containing `job_id` (or `id`) and `status`.
- `GET {base}/jobs/{job_id}`; return JSON with `status` and optionally `outputs: [{url, filename}]`.
- Output download URLs must be accessible to the worker. GLB files are downloaded into the worker output directory.

This is a provider adapter, not a bundled neural 3D model. A real model backend (local GPU or paid/free provider) must be installed and configured. No provider key is included.

## API docs
With the worker running, open `http://127.0.0.1:8765/docs`.
