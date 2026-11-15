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

The Agent tab now connects to the Termux worker API. It supports local-only model routing, a safe tool allow-list, an approval queue for destructive operations, and CPU-first procedural scene workers. See `worker/README.md` for Android setup and model configuration.

Start the worker from Termux with `cd ~/storage/downloads/JarvisSandbox/worker && bash run_termux.sh`. Generated assets are written to `~/storage/downloads/JARVIS_WORKSPACE`. No PC or cloud PC is required for the coordinator and procedural starter workers. A local GGUF inference server is required for general natural-language reasoning; deterministic scene recipes remain available without either model.

## JARVIS Swarm v0.4 status
The Swarm API is available at `/api/v1/swarm/agents` and `/api/v1/swarm/tasks`. It persists task plans, agent reports, messages and bounded per-agent memory under `JARVIS_WORKSPACE/swarm`. This release is an offline coordination foundation: it does not yet provide neural agent reasoning, image understanding, autonomous mesh generation, or live control of the Android Blender app. A local model runtime and a supported Blender bridge are later milestones.

## Local-only privacy mode
Remote LLM fallback and external image-to-3D provider calls are disabled in this build. The local model endpoint defaults to `http://127.0.0.1:8080/v1`. If no local model is running, the worker uses deterministic responses and records that reasoning is unavailable.
\nThe v0.4 Swarm endpoints are backend-ready but are not yet exposed as a dedicated Android screen. The existing AgentConsole remains the v0.3 chat/approval interface; the next Android milestone is a Swarm dashboard for agents, tasks, messages and memory.\n
## JARVIS Swarm Dashboard (v0.4)

The Android app now includes a **Swarm** tab alongside the existing Agent console. It connects to the local Termux worker endpoints:

- `GET /api/v1/swarm/agents` — list the registered agents
- `GET /api/v1/swarm/tasks` — view the task board
- `POST /api/v1/swarm/tasks` — create a coordinated task
- `POST /api/v1/swarm/tasks/{task_id}/run` — run the offline coordination pass

The dashboard shows each agent's role, task status and the coordinator's report. This is an offline task-coordination prototype, not autonomous neural reasoning: local GGUF inference, image understanding, Blender scene telemetry and actual mesh/rig generation remain future integrations. Cloud model fallback controls have been removed from the Android Agent screen; configure only a local OpenAI-compatible GGUF server.

Android app version: **0.4.0** (versionCode 3).

## JARVIS Character Forge v0.1 (offline starter)

The Swarm screen includes **Generate Rem Character**. It calls `POST /api/v1/character/generate` and creates a local GLB plus OBJ/MTL and a report under `JARVIS_WORKSPACE/outputs/`. The GLB is a deterministic, multi-part procedural anime-maid blockout with named mesh parts and palette materials. It does not call a cloud service or require a GGUF model.

This is the first geometry milestone, not a finished cinematic character: it has no UV unwrap, texture maps, production topology, skeleton, skin weights or animation. Those are subsequent Forge milestones. Download the GLB using the link returned by the endpoint or the dashboard's **Open / download GLB** action.
