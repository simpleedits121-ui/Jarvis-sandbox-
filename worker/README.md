# JARVIS Swarm Worker (Android / Termux)

This is the local execution gateway for JARVIS Sandbox. It runs on the same Android phone in Termux; no PC or cloud PC is required for the worker coordinator and procedural scene workers.

## Start on Android

1. In Termux, allow shared storage once:
   ```bash
   termux-setup-storage
   ```
2. Install Python if needed:
   ```bash
   pkg update -y && pkg install python -y
   ```
3. From the extracted repository:
   ```bash
   cd ~/storage/downloads/JarvisSandbox/worker
   bash run_termux.sh
   ```
4. Keep Termux running. In JARVIS Sandbox open **Agent**. The default worker URL is `http://127.0.0.1:8765`.

The Python virtual environment is kept under Termux's private home. Generated projects are stored in `~/storage/downloads/JARVIS_WORKSPACE` so they can be opened by Android apps.

## What is implemented

- Local model router: supports a local OpenAI-compatible model endpoint. Remote model fallback is disabled.
- Local CPU fallback: a built-in rule-based director can still create a procedural laboratory/room scene when no model endpoint is configured.
- Specialized lightweight workers: geometry, materials, world layout, cinematography/animation plan and quality validation.
- Scene outputs: `scene_preview.obj`, `scene_preview.mtl`, `scene_spec.json`, `scene.py`, and a README.
- Approval queue: deletion, overwriting an existing file and Blender script execution require explicit approval in the Android Agent screen.
- No unrestricted shell tool is exposed to the model.

## Connect a local GGUF model

Run a local inference server on the same phone that exposes an OpenAI-compatible `/v1/chat/completions` endpoint. For example, if you already have a compatible `llama-server` binary and a GGUF model, its command is typically similar to:

```bash
llama-server -m /path/to/model.gguf --host 127.0.0.1 --port 8080
```

The exact command and available flags depend on the llama.cpp build you install. In JARVIS Sandbox → Agent → Model settings, set:

- Local URL: `http://127.0.0.1:8080/v1`
- Local model ID: the model ID reported by that server (some servers accept `local-model`)

This project does not bundle model weights or claim a GGUF runtime is already installed. CPU inference quality and speed depend on model size, quantization and available RAM.

## Optional remote fallback

In Agent → Model settings, enter an OpenAI-compatible endpoint, model ID and your own API key. The key is saved under Termux private home at `~/.config/jarvis-sandbox/agent-settings.json` with owner-only file permissions; it is not stored in shared Downloads and is never returned by the config API. Remote model usage may incur provider charges. If the local model fails, the router tries this remote endpoint. If both are unavailable, deterministic local workers remain available for the built-in scene recipe.

## Blender / Android limitation

The local workers generate a real OBJ geometry preview and a deterministic Blender Python script. If a `blender` command-line executable is installed in Termux, the worker can run the script after explicit approval. The Android Blender app is a separate Android application sandbox: Termux cannot silently access its embedded Python or control its UI unless that specific Blender build exposes an automation interface. On Android builds without that interface, import `scene_preview.obj` in Blender and use `scene.py` only if the app supports its Scripting workspace. A `.blend` file is created only when Blender actually executes the script.

The OBJ preview is a lightweight blockout mesh; the Blender Python script uses the intended primitive shapes and materials. The first procedural character output is a mannequin placeholder, not a photoreal reconstruction, production facial rig or animation-ready human. Photo-to-identity 3D reconstruction remains a separate model integration milestone.

## Security

- Worker binds to `127.0.0.1` by default.
- Do not bind to `0.0.0.0` or expose the API to the internet.
- If you deliberately enable LAN access, set a long `JARVIS_ACCESS_TOKEN` and keep it private.
- AI tools cannot run arbitrary shell commands.
- Destructive operations and Blender script execution require approval.

## API

With the worker running, open `http://127.0.0.1:8765/docs` in a browser on the phone.

\n## Local-only mode (v0.4)\nRemote model fallback and external image-to-3D provider calls are disabled. Configure only a local OpenAI-compatible GGUF server. With no local model configured, deterministic workers and the Swarm coordination API remain available; they do not provide neural reasoning or actual Blender UI control.\n\n## Swarm API\n- `GET /api/v1/swarm/agents`\n- `POST /api/v1/swarm/tasks` with `{"goal":"..."}`\n- `GET /api/v1/swarm/tasks`\n- `GET /api/v1/swarm/tasks/{task_id}`\n- `POST /api/v1/swarm/tasks/{task_id}/run`\n- `GET /api/v1/swarm/tasks/{task_id}/messages`\n- `GET /api/v1/swarm/agents/{agent_id}/memory`\n

## Character Forge v0.6
The offline generator creates a smoother, more detailed stylized blue-haired maid character with indexed meshes, averaged vertex normals, layered eye geometry, curved tapered hair locks, a flared layered skirt, and separate garment/accessory parts. Outputs include GLB, OBJ, MTL, and a JSON report. This is still procedural stylized geometry: UV texture maps, production rigging, skin weights, animation, and cinematic reconstruction are not implemented.
