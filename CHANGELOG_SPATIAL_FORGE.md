# JARVIS Spatial Forge / Nano-Builder foundation

## Added
- Android Spatial Forge tab for Boss orders, scene refresh, component listing and worker activity.
- Local SpatialEngine with persistent JSON scene graph and construction event history.
- Validated JSO operations: create primitive, transform, assign material, rename and delete.
- Staged surveyor, structural, skin, detail and inspector workflow.
- OBJ blockout export endpoint.
- Spatial engine unit tests and architecture notes.

## Honest limitations
This is a mobile-first foundation and proof of the worker/scene workflow. It is not yet a physically simulated nanobot system, autonomous neural worker intelligence, detailed character sculpting, image segmentation, production UV/texturing or production rigging. The current demo creates editable primitive blockout components. These capabilities are planned as subsequent implementations, not represented as complete.


## v0.5.0 — Interactive 3D blockout viewport
- Added a lightweight Compose Canvas 3D projection viewport for the existing local scene graph.
- Added drag-to-orbit and pinch-to-zoom camera gestures, a spatial floor grid, shaded component faces, and region-based colors.
- Scene refresh now reads component IDs, primitive types, transforms, scale and region from the worker response.
- Kept rendering dependency-free to reduce APK size and avoid introducing a heavyweight 3D engine before profiling on the target phone.
- The current viewport renders primitive blockout proxies; it is not a production mesh renderer and does not yet render GLB materials, skeletons or animation.
