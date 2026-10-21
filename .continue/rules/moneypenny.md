# Moneypenny Studio workspace rules

Moneypenny Studio is a production pipeline for a realistic adult 3D virtual companion and assistant. Keep these goals together:

- low-latency, interruptible two-way voice with synchronized mouth movement;
- persona-controlled dialogue, gestures, idle behaviour, autonomy, quiet periods, and timed follow-ups;
- fluid full-body movement using the existing rig, IK, correctives, and imported animation clips;
- Blender-authored poses and animation clips that are exported and retargeted into the web studio;
- realistic PBR skin, eyes, lips, hair, hands, and feet;
- fitted, changeable clothing and footwear that preserve the body rig;
- optional future integration with Jarvis services without coupling this studio to trading systems.

## Work in the real architecture

- `app.py` owns the Flask server and APIs.
- `motion.py` validates declarative movement plans.
- `static/action-commands.js` routes spoken phrases to supported actions.
- `static/motion.js` and `static/rig.js` own live procedural body movement and rig control.
- `static/motion-library.js` owns imported clip storage, retargeting, playback, trigger phrases, and wardrobe markers.
- `scripts/character/studio_controls.py` owns Blender pose capture, smooth pose transitions, and animation-only GLB export.

The active checkout is `/Users/jamesjohnston/Documents/Moneypenny-Studio`. Do not use the separate Desktop checkout. There is no `animations.py` source file. Do not invent `src/main.py`, Pygame scaffolding, paths, functions, tool results, or commands.

Read the relevant existing files before proposing or applying a change. Prefer one small extension to the current architecture. Preserve unrelated changes, Git history, Blender files, and backups. Never claim an edit, test, render, animation, export, commit, push, or deployment succeeded without direct tool output proving it.

Do not delete, move, rename, install, commit, push, or run broad terminal commands unless the user explicitly requests that action.

## Current character and 4D source map

Read `GEMINI_HANDOFF.md` and `CHARACTER_SOURCE_PROVENANCE.json` before character work. The root `Moneypenny-Adult-Body-Source.blend` is the original editable adult base. Live v38 remains the fallback. The Aliyah/Claudia captures are separate clothed studies; the 4D workshop is recorded playback, not a hidden complete body or autonomous motion generator. Use the named launchers or VS Code tasks. Preserve original scenes and save a new version.
