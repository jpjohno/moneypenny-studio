# Moneypenny Studio handover

Updated: 18 October 2026. Checkout: `/Users/jamesjohnston/Documents/Moneypenny-Studio`. Repository: `jpjohno/moneypenny-studio`, branch `codex/live-3d-persona`, draft PR [#1](https://github.com/jpjohno/moneypenny-studio/pull/1). Local URL: http://127.0.0.1:8090.

## Current implemented behaviour

- TalkingHead/Three.js rigged character, gaze, expression, mouth shapes driven from the actual Kokoro audio through HeadAudio. British `bf_emma` voice identity remains fixed.
- Ollama NDJSON answer streaming with conversation history. Speech starts from ready phrases before the complete answer arrives, prefetching synthesis while the current phrase plays. Context is 4096 tokens, matching the existing Jarvis route and avoiding context-size runner reloads.
- One-click live microphone activation, local Silero V5 speech detection and Whisper transcription, automatic turn submission, speech-onset mute/cancellation and rejection of stale turns. Record note remains a separate review-before-send option. Stop live mode closes the stream.
- Quiet/resume commands and saved timed follow-ups in ignored `.runtime/reminders.sqlite3`. A visible open tab claims each due item once; closed tabs/sleeping Macs cannot deliver until available again.
- Separate body motion director: shoulder/body reach IK, jig/dance, walk, turn, stretch, bow, sit, kneel, lie on back, splits, and bounded custom joint timelines. Persona-driven procedural movement runs independently of chat. Model-generated choreography is optional and OFF by default because it competes with conversation for the same local model.
- Actual additional skinned prototype skirt, waistcoat, dress-skirt and shoe meshes. Original sample outfit remains underneath for coverage. Selecting outer layers is a mesh swap, not physical dressing simulation.
- Custom persona/settings import/export, browser persistence and imported compatible GLB retention. Photography is a reference only, not a rig.
- Loopback-only Flask service, Host/Origin/custom-header protection, local-only asset CSP and bounded input. Separate owned voice/listening subprocesses reuse existing model files read-only. SIGINT/SIGTERM close owned workers; Jarvis/Ollama services are not taken over.

## Files added in this upgrade

| File | Purpose |
| --- | --- |
| `listening.py` | Private warm whisper.cpp process with Vosk fallback |
| `static/live.js` | VAD, audio capture, phrase segmentation, synthesis/playback pipeline and quiet/timer parsing |
| `motion.py`, `static/motion.js` | Validated motion plans, local full-body controller and reach IK |
| `static/wardrobe.js` | Separate skinned prototype garments and footwear |
| `reminders.py` | Persistent follow-ups and atomic delivery claim |
| `tests/test_live_features.py`, `tests/live.test.mjs`, `tests/motion.test.mjs` | Behaviour, cancellation/prefetch, reminder concurrency and actual sample-rig checks |
| `PHOTOREAL_CHARACTER_SPEC.md` | Concrete production asset/rig/wardrobe brief and current gaps |
| `BUSINESS_PLAN.md` | Standalone product proposal and optional future Jarvis integration |

`app.py`, `static/studio.js`, the template, styles, setup and launcher connect these systems. Vendor revisions/checksums remain in `assets-manifest.json`; npm dependencies are pinned in the lockfile.

## Verification on this Mac

- 30 Python tests and 10 Node tests passed; JavaScript syntax checks passed. npm audit reported zero vulnerabilities after the VAD installation.
- Actual warm Whisper process started in 0.34 seconds. A generated British voice phrase was transcribed in 0.66 seconds as “Hello James, shall we make something rather good together?” These are local single-run measurements, not microphone acoustic-quality tests.
- Browser Start live conversation reached “Listening · speak naturally”, with a changing microphone speech-probability meter and no fresh console errors. Stop live conversation returned to “Microphone off”, meter zero. No microphone remains open after testing.
- Actual streamed conversation: first voice at 3.80 seconds, complete model reply at 7.47 seconds in one warm run. This confirms playback before completion, not zero latency. Cold voice preparation took 3.12 seconds for “Ready.”
- A background model choreography request caused roughly 26 seconds of queuing in an earlier test. It was removed from the default loop; independent procedural movement continues without model inference. Optional model choreography may still compete for the same model when explicitly enabled.
- Quiet button exposed Resume voice; resuming and submitting “Ask me in three seconds” saved a real follow-up, then displayed its check-back message and cleared the pending database item.
- Original browser tests also verified conversation memory, preview playback, Stop/cancellation and responsive layout. Tests now cover prefetch during playback, cancellation, bounded custom joint data and single-claim follow-ups across concurrent tabs.

## Unfinished requirements and acceptance limits

- **Photographic realism is not achieved.** Current person remains a generic CC0 MPFB sample. Skin, face, hair, eyes, full adult anatomical source body, fitted underwear, professional clothing/shoes and corrective shapes need actual asset production/import and inspection. Do not mark them complete or imply that light/material changes supplied them.
- Wardrobe and body movements are procedural prototypes. No cloth simulation, true removal/putting-on animation, production contact/collision system, natural locomotion library or guarantee of arbitrary human movement. Extreme poses can show deformation/fit limitations.
- HeadAudio mouth timing is approximate. Fluid phrase buffering exists; human listening acceptance and actual acoustic barge-in/echo testing on speakers/headphones remain unverified. The browser microphone-start check does not prove those.
- Character file upload acceptance was explicitly declined by the browser approval system in the first turn. No alternative upload path was attempted. Coding/static compatibility checks exist; successful UI import/persistence remain unverified.
- No MetaHuman account, licence acceptance, installation or production character was obtained. No user portrait, private media or non-commercial sample was substituted or published.
- No Jarvis action adapter, communication sends, trading connection, accounts, cloud sync or public production deployment. Jarvis is a future optional provider, not a required runtime.
- Fresh independent voice installation on another machine remains unverified. The verified machine reuses existing local model/runtime files read-only.

## Runtime and continuation

Open `Start-Moneypenny.command`. It detects an existing studio and never kills another app occupying its port. Keep the app's terminal open. Nothing was installed as a LaunchAgent.

Whisper uses the official pinned English base model in `.runtime/whisper-models/ggml-base.en.bin`, SHA-256 `a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002`. `scripts/setup.py --whisper` installs that model when whisper-server is already available. Machine paths are in ignored `.runtime/machine.json`.

Read-only reuse references: the existing JJRVIS communication broker workspace, Enki Sticker Studio source and earlier Enkidu video compositor. No synced `sources/` files were modified. Personal media, audio, models, environments, machine configuration, reminders and screenshots are excluded from public Git history. `app 2.py` is a preserved ignored original backup.

Next significant work is the production character package described in `PHOTOREAL_CHARACTER_SPEC.md`, followed by visual/motion and acoustic acceptance with the actual user hardware. The current local code upgrade must not be represented as the completed photo-real product.
