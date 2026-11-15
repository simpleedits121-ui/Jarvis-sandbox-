# JARVIS Nano-Builder — mobile-first implementation

## What this build delivers
- A local editable scene graph stored under `JARVIS_WORKSPACE/spatial/`.
- A validated Spatial Operations (JSO) API for creating primitives, transforms, material assignment, rename and delete.
- A staged local construction workflow with surveyor, structural, skin, detail and inspector worker events.
- Persistent scene and construction history.
- Android Spatial tab to issue a Boss order and inspect components/activity.
- OBJ blockout export endpoint.

## API
- `GET /api/v1/spatial/scene`
- `POST /api/v1/spatial/operations`
- `POST /api/v1/spatial/nano-build` (JSON `{ "goal": "..." }`)
- `GET /api/v1/spatial/export/obj`

## Honest capability boundary
This is the first executable Nano-Builder foundation. The visible worker activity corresponds to actual staged scene operations, but workers are deterministic local task workers, not independent neural minds. The current face/character demo is a primitive blockout, not detailed anatomical skin, photorealistic texturing, automatic segmentation, or production rigging. The OBJ export is a blockout export. Existing Character Forge, Swarm, rigging code and AETHER documentation are retained.

## Mobile constraints
The Android app remains the control surface; the Termux Python worker performs local scene operations on the same phone. No cloud service or external 3D API is called by this subsystem. Geometry updates are incremental and scene data persists locally.
