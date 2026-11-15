# JARVIS Sandbox v0.7 — Humanoid Rigging

## Added
- 17-joint humanoid skeleton in exported glTF/GLB.
- Per-vertex `JOINTS_0` and normalized `WEIGHTS_0` attributes on every generated mesh primitive.
- Inverse bind matrices and a valid glTF skin referencing the joint hierarchy.
- Generation report now records joint count, skinned mesh count, and animation clip count.

## Not included yet
- Animation clips, facial blend shapes, UV texture maps, and physically simulated garment deformation.
- The existing procedural character geometry is intentionally retained; this release advances rigging, not visual appearance.

## Validation
- Python unit tests inspect GLB header, skin, joint count, and skinning attributes.
- Android Gradle build must still be run by the user or GitHub Actions.
