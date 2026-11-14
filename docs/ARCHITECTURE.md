# JARVIS Sandbox architecture

## Target topology
- Android app: native Kotlin/Jetpack Compose control surface, local files, image upload, approvals and job monitoring.
- Android worker: Termux Python service bound to loopback for same-device tools.
- PC worker: same API on a paired computer for desktop Blender, larger Python jobs and GPU inference.
- Optional cloud worker: separately configured remote execution endpoint.
- Agent runtime: OpenAI-compatible chat-completions endpoint with a constrained tool registry.
- Asset pipeline: image-to-3D provider adapter → GLB output → Blender bridge → JARVIS Character Forge/AETHER.

## Trust boundaries
1. Android app-private storage is the default.
2. Worker workspace is a dedicated directory, not the whole phone filesystem.
3. No unrestricted shell endpoint is exposed.
4. File deletion requires explicit confirmation.
5. Remote worker binding requires an access token.
6. Provider credentials are environment variables and must never be committed.

## Image-to-3D
A single image is underdetermined: rear geometry, hidden limbs and occluded surfaces are inferred. A production result needs a compatible image-to-3D inference backend. The included worker implements a documented provider adapter and job lifecycle; it does not bundle a multi-gigabyte neural model or pretend to generate a model without one.
