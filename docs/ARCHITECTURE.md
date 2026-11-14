# JARVIS Swarm Architecture (v0.3)

## Execution topology

- Android app: UI, worker connection, model settings, chat, approvals and file exchange.
- Termux worker: local FastAPI gateway bound to loopback; owns the workspace and executes allow-listed tools.
- Brain routing: local OpenAI-compatible GGUF endpoint first; optional remote OpenAI-compatible model second; deterministic local worker recipe as final fallback.
- CPU worker team: geometry, materials, world layout, cinematography/animation planning and quality validation. These are lightweight deterministic modules, not multiple large neural networks.
- Blender adapter: creates a safe Blender Python scene script and OBJ/MTL preview. It can run a Blender CLI only if one is actually installed in Termux; Android Blender's app sandbox is not silently controlled.

## Request lifecycle

1. User sends an instruction from Agent screen.
2. Android sends the message and recent conversation history to `/api/v1/agent/chat`.
3. Worker tries local model; on failure it tries the configured remote endpoint.
4. Model returns a JSON plan using the fixed tool allow-list.
5. Worker validates arguments and invokes local tools.
6. Destructive operations create approval records; the app displays Approve / Reject controls.
7. Scene tasks delegate to CPU workers and create a project folder with OBJ, MTL, JSON spec and Blender Python script.

## Safety boundaries

- No arbitrary shell execution is exposed to the model.
- Workspace paths are canonicalized and traversal is rejected.
- Existing-file overwrites, deletion and Blender script execution require approval.
- Worker binds to localhost by default. LAN binding requires an access token.
- Remote API credentials are stored under Termux private home (`~/.config/jarvis-sandbox/agent-settings.json`) with owner-only permissions; they are not returned by the settings endpoint.

## Current limits

- No GGUF weights or inference binary are bundled. A local OpenAI-compatible inference server must be installed separately to activate the local model brain.
- A remote API key is optional and user-supplied; remote inference may cost money.
- Procedural scene workers currently create a starter room/lab and mannequin placeholder. They do not reconstruct a real person from a selfie, produce a professional humanoid rig or guarantee cinematic-quality rendering.
- Android Blender may not expose its embedded Python to Termux. If no Blender CLI is available, the worker exports an OBJ preview and a Blender Python script for an app that supports importing/running them.

## Existing JARVIS / AETHER preservation

This release changes only the separate `Jarvis-sandbox-` repository. It does not modify, replace or delete the existing `Jarvis` Android application, AETHER renderer, character assets, CharacterEngine, CharacterController or DesktopMateService. Outputs can be exported from `JARVIS_WORKSPACE` and imported into the existing JARVIS project through its existing asset workflow. A future authenticated project-sync adapter can connect the two repositories without merging their build systems.
