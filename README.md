# JARVIS SANDBOX

Independent Android-first workspace for developing the JARVIS ecosystem.

## v0.2 includes
- Kotlin + Jetpack Compose Android app
- App-private file manager and import/export
- Restricted local terminal commands
- AI task queue UI
- 3D Lab: choose a reference image, test the worker, submit an image-to-3D job
- Python FastAPI worker for workspace operations, task queue and 3D provider jobs
- Blender desktop asset import/export helper
- GitHub Actions workflow to build a debug APK on push

## Run on Android
1. Install Python in Termux: `pkg install python`.
2. Copy this repository into Termux home if shared storage permissions cause issues.
3. Run `cd worker && bash run_termux.sh`.
4. Open JARVIS Sandbox → 3D Lab → Test worker.
5. Select a reference image and submit it.

## Build APK
Push to GitHub. The `Android APK` workflow builds the debug APK and uploads it as an Actions artifact. Open the repository's Actions tab, open the latest successful run, and download `jarvis-sandbox-debug-apk`.

## Image-to-3D truth
The app and worker now implement the upload/job pipeline. Actual 3D inference requires a compatible image-to-3D provider configured on the worker using `JARVIS_3D_PROVIDER_URL` (and optionally `JARVIS_3D_PROVIDER_TOKEN`). The worker documents its provider contract in `worker/README.md`. No paid service, API key, or model weights are bundled. A single image cannot reveal unseen geometry; the model estimates it.

## Android / Blender
Android Blender can exchange `.blend`, `.glb`, `.gltf`, `.fbx`, `.obj` and texture files through Android's document picker. The included Blender helper is for desktop Blender when a PC is available; it adds GLB import/export buttons.

## Security
The worker defaults to loopback only. It exposes no arbitrary shell. Remote binding requires a token. Keep it off the public internet.

## Push from Termux
From the extracted project directory run:
```bash
bash push_to_github_termux.sh
```
The script registers the shared-storage path as a safe Git directory, configures the repository remote, asks for commit identity only if missing, and pushes `main`. GitHub may prompt for a Personal Access Token or other configured authentication.


## JARVIS Swarm v0.3 (local-first AI operator)

The Agent tab now connects to the Termux worker API. It supports local-first / remote-fallback model routing, a safe tool allow-list, an approval queue for destructive operations, and CPU-first procedural scene workers. See `worker/README.md` for Android setup and model configuration.

Start the worker from Termux with `cd ~/storage/downloads/JarvisSandbox/worker && bash run_termux.sh`. Generated assets are written to `~/storage/downloads/JARVIS_WORKSPACE`. No PC or cloud PC is required for the coordinator and procedural starter workers. A local GGUF inference server or optional remote API is required for general natural-language reasoning; deterministic scene recipes remain available without either model.
