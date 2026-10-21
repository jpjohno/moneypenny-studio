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
- **Existing live assistant:** `.runtime/character-workshop/Moneypenny-Style-v39.glb`.
  The v38 export remains the previous-look comparison and loading fallback. v39 contains
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
  are specific to that study; do not conflate them with the live v39 face.

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
editing. Save a new version, preserving the original base and working v38/v39 exports. Develop
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

## Latest verified refinement, 21 October 2026

`refine_look_v39.py` builds the local clothed v39 candidate from v38. It replaces
sparse brow filaments with a short surface-following groom, reduces the crown
height and relaxes shallow blouse dents. Original face/body Basis and all 76
body target coordinates, hand/eye/teeth geometry, 54 bones and garment
UVs/weights/topology are retained. The default app and previous-look comparison
now report their actual revisions instead of hard-coding the older comparison.

The runtime resting smile now releases during speech instead of adding a held
smile to closed consonants. Conversational open-palm gestures use the local rig
controller so the neutral-body reset does not erase them. PCM/envelope start
clocks are shared; interruption fades remain connected until the scheduled
stop; delayed old audio stays muted during fast replacement. Explicit movement
commands retain priority. Hair tint no longer duplicates v39's authored colour.

The installed Mac app visibly loaded `style-v39` and performed the wave. The
Studio preview visibly reached Speaking with an open-palm movement and returned
to idle without a playback error. Acoustic quality and exact lip timing have
not been certified from that visual check. See `PORTRAIT_SPEECH_VERIFICATION.json`.

**Photographic appearance is still unfinished.** Coarse hair cards, broad baked
highlights in the 1K atlas and the existing generic skin maps remain. Do not
claim that more samples or hundreds of parameter variations resolve those
source limitations. New runtime binaries remain private; the build and fixes
are published as source. No new photographic character was downloaded.

## Animation and voice follow-up, 21 October 2026

`static/animation-builder.js` and the Create an animation panel now provide local
ordered movement creation, Preview/Stop, save/reopen and sequence JSON export/
import. `motion_assets.py` validates and stores `.sequence.json`; the library
plays it through the existing MotionDirector instead of duplicating bone poses.
Nine ordinary skills are exposed, at most eight steps. Imported/baked clip pause,
seeking and garment cues remain separate from sequence playback.

The shared appearance reader was incorrectly calling the POST helper with no
body and silently keeping old settings. It now uses GET, reports sync status and
re-applies shared choices after loading an older saved persona. Light blonde
raises the authored hair factor; Brighter blue masks only the actual iris UV
annuli, preserving pupils, whites, maps, geometry and facial shapes. This is a
reversible presentation change, not a new photographic character source.

The private broker voice update is in
`integrations/jjrvis/jjrvis-voice-identity.patch`, with exact basis hashes and
verification. A reply keeps one profile/speed across all phrases and rejects
unexpected voice metadata. Both British local voices were verified after broker
restart. The existing bf_emma sound and owner preference were preserved; the
reported changed accent was not acoustically reproduced. After the owner
unlocked the native app, the workspace was reloaded and visibly showed v39,
the blonde/blue palette, a working Wave and the local Create animations link.
The Studio save/reopen/Preview/Stop workflow was also checked live. No microphone
or acoustic playback certification was performed in this follow-up.

## Movement and mouth repair, 21 October 2026

The current update fixes lost elapsed time under dropped frames and carries
queued steps across their real boundaries. A nominal 2-second sequence formerly
took 4.6 seconds at 5 fps; actual skeleton tests now finish at 2 seconds at both
5 and 60 fps. Duration-relative fades let short gestures reach their pose.
Builder Preview explicitly uses 1x/single play and stops local speech immediately
while cancelling old backend synthesis in the background. No new render loop.

The local HeadAudio adapter repairs a falsy-zero test that skipped viseme_aa and
releases the active mouth target on reset. Lip interpolation uses the audio clock
rather than a clamped body-frame delta. Reapplying the same mood now preserves
ongoing gaze, blink and head tracks. Conservative trailing-quiet trimming keeps
80 ms after the active window, removes at most 350 ms, and preserves leading and
retained PCM samples. Both voice and lip analysis receive the same resulting
buffer. The tested greeting clips each lose 160 ms of confirmed quiet.

A reversible blonde-only shader correction reduces the pink accent fibres.
No face/body geometry, alpha mask or texture was replaced. Coarse hair cards and
source skin detail still limit realism. See MOTION_SPEECH_REPAIR_VERIFICATION.json
for current evidence and limits.

Native QA after owner unlock visibly reached Speaking with mouth movement and a
presentation gesture, and a batched Replay→Stop check reached VOICE STOPPED.
Wave and the saved 7-second wave/bow sequence completed. A broad voice-help
matcher exposed by this test is isolated in the exact-basis private broker
overlay `integrations/jjrvis/jjrvis-voice-help.patch`; it also repairs a stale
Speaking badge after Stop. No microphone was opened in this follow-up. Visual
playback and automated clock checks do not certify acoustic alignment.

The anchored “say exactly: TEXT” utility returns at most 400 characters locally
without a model call or device action; embedded quotations do not activate it.
The native literal phrase and Replay→Stop/3D READY checks passed after the
coordinated broker restart. The current pass has 134 Studio Node checks and
89 focused broker Python plus 21 broker JavaScript checks passing.
