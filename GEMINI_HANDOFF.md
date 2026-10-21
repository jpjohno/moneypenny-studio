# Moneypenny character and 4D workshop handover

Updated 21 October 2026. Repository: https://github.com/jpjohno/moneypenny-studio
Branch: `codex/live-3d-persona`. Local project:
`/Users/jamesjohnston/Documents/Moneypenny-Studio`.

## Requested result

Develop a fictional adult Moneypenny with an attractive youthful adult face,
blonde hair, blue eyes, a warm smile and a fuller, balanced figure. The user wants
photographic skin, believable hair and eyes, fluid body motion, synchronised
speech and separate well-fitted clothing. Work from a neutral adult body for
nonsexual proportion and garment-fit review, then add fitted garments. Keep all
tools and source inputs free.

These are goals, not a statement that photographic quality or unrestricted
autonomy has been achieved.

## Start with the correct asset

- **Editable body base:** `Moneypenny-Adult-Body-Source.blend` at repository root.
  This exact saved parametric source is now included for handover. It has a
  19,158-vertex adult body, five keys including Basis and a 52-bone body rig.
  Its main body does not have the finished speaking face, production hair, eyes
  or wardrobe. A hidden clothed sample is a reference, not the body to edit.
- **Existing live assistant:** `.runtime/character-workshop/Moneypenny-Style-v38.glb`.
  Preserve this working fallback while developing the replacement. It contains
  15 named viseme slots, body controls and expressions. Keep its existing voice
  interruption, microphone permissions, Stop and persona behaviour working.
- **Older anatomy study:** root-level `Moneypenny-Adult-Anatomy-Study-v3.blend`
  was already tracked before this handover. It differs from the similarly named
  runtime copy. It is an unfinished legacy study with unresolved component
  licensing, not the preferred clean parametric starting point. Do not confuse
  these two files or claim the older study is absent from Git.
- **Recorded 4D capture:** Aliyah dance004 is a real captured clothed person.
  Its mesh connectivity and UVs change across frames. It has no underlying
  separate unclothed body and no conversational skeleton. Recolouring or hiding
  captured clothing cannot turn it into a complete new person.
- **Claudia scanned study:** a separate clothed scan with an experimental facial
  bake. Its 14 approximate articulating shapes plus unchanged neutral silence
  are specific to that study; do not conflate them with the live v38 face.

## Local launchers and files

Double-click **Open Moneypenny Body Source.command** for the editable base.
Double-click **Open 4D Capture Workshop.command** for the prepared moving scan.
The same actions are available as tasks in `Moneypenny.code-workspace`.
Blender opens in a separate process with embedded source scripts disabled.
Existing Blender windows and unsaved work remain untouched.

The 4D workshop file is:
`.runtime/scan-review/renderpeople-4d/workshop/Moneypenny-4D-Capture-Workshop.blend`.
Its original Alembic cache and matching 2K texture sequence remain in
`.runtime/scan-review/renderpeople-4d/`. The prepared workshop resolves their
local paths and documents the recorded-performance limits.

The browser review is http://127.0.0.1:8090/realism . It offers the complete
37-second captured clip, camera orbit, scrubbing, play/pause and 512px/1024px
picture options. It retains at most three decoded frames. This is playback and
authoring preparation, not hardware or software that records a new 4D person.

## Work in the existing architecture

Use Blender's actual mesh/material/rig tools and inspect the saved scene before
editing. Save a new version, preserving the original base and live v38. Develop
body proportions and a convincing face first, then skin/eyes/hair, speaking face
controls, garment fit, corrective deformation and tested animation clips. A
still image, shader colour change or higher render-sample count is not a complete
photographic 3D character. Recorded 4D animation cannot be treated as a compatible
humanoid motion clip without a separate validated reconstruction/retargeting step.

`app.py` serves the studio; `static/studio.js` loads the conversational character;
`static/rig.js` and `static/motion.js` control its body; `static/fourd-player.js`
and `static/realism.js` implement the separate recorded preview. The public
scripts `scripts/character/prepare_4d_workshop.py` and
`scripts/character/convert_4d_review.py` prepare authorised local capture inputs.

For a replacement browser character, export a self-contained GLB with compatible
humanoid bones and validated speech/expression shapes. Check front, side, rear,
close-up, wave, movement recovery, mouth closure and clothing intersections in
the real renderer. Show actual review images and report what remains unfinished.
Do not replace the working default until those checks pass.

Run `.venv/bin/python -m pytest -q`, `npm run check` and `npm test` after relevant
code changes. Avoid Pygame scaffolding, invented source files or blind rewrites
of `app.py`. Keep communication and character work separate from trading.

## Access and publication

GitHub now contains the original editable body base, source, tests, launchers and
this handover. See `CHARACTER_SOURCE_PROVENANCE.json` for exact hashes and source
licences. Renderpeople capture data, prepared workshops, later runtime character
exports, private configuration and recordings remain local. A fresh clone cannot
play the captured sample without its authorised local data. Customer distribution
of the captured/legacy assets is not cleared by this handover.

Gemini needs real local file and Blender execution access to perform these edits.
A web-only chat cannot inspect or modify a Mac file merely from its written path.
State a missing input or tool clearly instead of claiming an edit or render ran.
