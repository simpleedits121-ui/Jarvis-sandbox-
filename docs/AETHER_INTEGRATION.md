# Existing JARVIS / AETHER integration boundary

The original `simpleedits121-ui/Jarvis` repository remains a separate application and is intentionally untouched by JARVIS Sandbox Swarm v0.3.

Preserved upstream areas include the existing `CharacterAvatar`, `CharacterController`, `CharacterEngine`, `CharacterModels`, `DesktopMateService`, capability registry, `JarvisCore`, character artwork and imported AETHER renderer assets.

The Sandbox worker currently exports standard files (`.obj`, `.mtl`, `.py`, `.json`, and future `.glb` outputs) into `~/storage/downloads/JARVIS_WORKSPACE`. These can be imported into the existing JARVIS app's asset workflow. The two Android apps do not share private app storage automatically, so this release does not claim live shared-memory or direct AETHER runtime control.

Future integration should use a versioned asset manifest and an explicit import/sync action. It must not overwrite AETHER source, model files or character assets without a user-approved backup and change plan.
