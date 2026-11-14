# JARVIS Swarm v0.3 implementation notes

## Included in this update

- Android Agent tab is now a real HTTP client for the Termux worker rather than a local draft queue.
- Local-first model routing with optional remote API fallback.
- Provider settings screen; remote API key is write-only from the app and stored in Termux private home.
- Conversation history is sent to the worker.
- Fixed tool registry for listing/reading/creating files and creating procedural Blender scene packages.
- Approval queue for deletion, overwrite and Blender script execution.
- CPU-only procedural worker team that writes an OBJ/MTL blockout, scene specification and Blender Python script.
- Termux workspace output path in Android Downloads.
- Existing JARVIS/AETHER repository is not modified; see `docs/AETHER_INTEGRATION.md`.

## What is not included yet

- No GGUF weights or llama.cpp binary are bundled. Install a local OpenAI-compatible inference server and set its model ID in Agent settings to activate local reasoning.
- No remote API key is bundled. Add your own key if you want remote fallback.
- The current scene worker builds a procedural room/lab and mannequin placeholder. It does not reconstruct a real person from a selfie.
- Termux cannot silently control the Android Blender app's embedded Python unless that app exposes a bridge. If a Blender CLI is available, approved background execution is supported; otherwise use the OBJ preview and generated Blender script.
- This release has not been compiled into an APK inside this container because an Android SDK/Gradle installation is not available here. Push the update to GitHub and use the existing Actions workflow to build the APK.

## Validation performed

- Python worker tests: 10 passed.
- Python source compilation: passed.
- Termux startup shell syntax check: passed.
- GitHub Actions Android compilation: not yet run for v0.3; check Actions after pushing.
