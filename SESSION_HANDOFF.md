# Moneypenny Studio handover

Updated: 18 October 2026. Checkout: `/Users/jamesjohnston/Documents/Moneypenny-Studio`. Repository: `jpjohno/moneypenny-studio`, branch `codex/live-3d-persona`, draft PR [#1](https://github.com/jpjohno/moneypenny-studio/pull/1). Local URL: http://127.0.0.1:8090.

## Current continuation: motion library and source workshop

Latest body continuation: actual `.runtime/character-workshop/Moneypenny-Adult-Anatomy-Study-v3.blend` built and opened in Blender. `Open Body Editor.command` now prefers it; `Build Adult Anatomy.command` can reproduce the data/setup/build. Original body/workshop and earlier study versions preserved. Body has 13,848 vertices, 13,828 faces, 52 bones, a welded 168-face external anatomical patch, nipple/navel details, shallow perianal surface contour, 478 individual skinned body-hair strands, fitted eyes/teeth/tongue/brows/lashes/ponytail/fingernails/toenails and five named Blender shape controls. `scripts/character/body-assets.json` pins official CC0 system/nail packs and the legacy patch data. Its embedded AGPL3 notice conflicts with the author's broad CC0 clarification: local authoring only; commercial redistribution explicitly not cleared. No legacy addon code was installed/run and no generated model/media/assets were published. The live speaking avatar remains unchanged.

Read-only saved-scene checks in `scripts/character/inspect_anatomy.py` passed: zero nonmanifold edges, zero unweighted vertices, all five morph-control extremes finite, moderate arm/leg posing finite with 0.371 m maximum displacement. Neutral front/rear/side renders were visually inspected, as was the actual Blender viewport. Photographic realism, extreme-pose corrective deformation, cloth fit and browser facial visemes remain unfinished. The perianal feature is a shallow closed external contour, not internal anatomy or medical certification. No declined character upload was retried.

Hugging Face update: the user submitted the access form themselves and supplied a subsequent screenshot showing **Meta Llama 3 ACCEPTED**. Approval is therefore evidenced by the user screenshot; local native-token authentication and a full text-conditioned ARDY test are still pending. Do not repeat the stale earlier statement that the form is unsubmitted or equate approval with a completed model download.

Further continuation: genuine NVIDIA ARDY source is pinned by `ardy-manifest.json` in ignored `.runtime/ardy`; dedicated `.runtime/ardy-venv` installed its native ARM64 motion-correction extension and downloaded the Core checkpoint. `load_model('core',device='cpu',text_encoder=False)` succeeded. A genuine unconditioned Core benchmark generated 40 frames/2 seconds in 1.115 seconds after 2.126-second loading, at the default 10 denoising steps. This excludes text encoding/contact correction and is not proof of prompt following or end-to-end real-time quality. A real required-model request returned `GatedRepoError`; no HF token/authorised encoder cache exists. The experimental MPS test required float32 conversion before placement; consult its private log for current outcome. No Rosetta or Parallels was installed. `scripts/ardy/convert_motion.py` exports actual Core rotations/root movement as animation-only GLB; a distinct 27-joint fixture passed GLTFLoader and retargeting checks. Two optional conversion tests passed in the dedicated environment; main Python suite remains 35 passed, 2 optional skips. See `NVIDIA_MOTION.md` and the two NVIDIA launchers.

Read-only existing Windows VPS check: 2 logical processors, about 4 GiB RAM; nvidia-smi unavailable. Graphics-adapter querying was not completed due remote keyboard mapping, so do not assert hardware absence. No ARDY installation or service/port changes were made on that VPS; user steered to Mac testing. No trading controls were changed. Remote Desktop keyboard was returned to Scancode after inspecting Unicode mode.

The corrected experimental Metal benchmark also completed: 2-second unconditioned motion core in 3.631 seconds, loading 2.836 seconds. It loads on CPU, converts floating buffers to float32, moves to MPS and updates ARDY's explicit device field. Initial direct-MPS placement failed on float64 buffers and initial moved model failed on a stale CPU device field; neither is hidden. This is one cold core run, not a full text/quality comparison; CPU stays the generation CLI default.

Earlier account setup: the user created and email-verified a Hugging Face account. The actual required model page was opened in their signed-in Chrome session and its access form expanded; submission was handed to the user. They subsequently submitted it and supplied an ACCEPTED screenshot, as recorded above. A separate `Connect NVIDIA Text Model.command` runs the vendor's local sign-in and checks access without asking for a token in chat. Do not equate email verification with model access. Do not copy the email-confirmation URL, date of birth, tokens or contact details into Git or handovers.

`Open Body Editor.command` opens the newly built separate `.runtime/character-workshop/Moneypenny-Adult-Body-Source.blend`, with an actual MPFB adult body/52-bone rig, source body-shape profile, preserve-volume deformation, smooth subdivision and initial textured/procedural skin. The existing performance workshop is preserved. Detailed anatomy/face/hair/nails/garment fit remain unfinished and are explicitly unverified in its local report. `static/appearance.js` improves only the bundled sample's skin/eye materials (preserving texture/rig/mouth data), adds lighting/brightness choices and preserves imported production materials. The close-up camera framing was corrected.

The previous engineering prototype was extended with an actual animation asset library, rig controls and named persona persistence. Earlier measurements below describe their original checks; this section records the new scope.

- `static/motion-library.js`: GLB/BVH and authored motion timelines, clone-based retargeting with Three.js SkeletonUtils, crossfades, pause/resume, looping, playback speed, per-bone source mapping, named movement words and timed garment markers. Late animation loads are invalidated by Stop. New local assets are persisted by `motion_assets.py` in ignored `.runtime/motion-library`.
- `static/rig.js`, `static/rig-view.js`: stable reference reset removes upstream hip-balance feedback; geometric two-bone IK preserves lengths and clamps unreachable targets; time-based interpolation; 3D translation handles, skeleton display, feet planting and hand/foot/hip sliders. Uncontrolled idle/voice gestures remain owned by TalkingHead. Splits use grounded leg IK and hand targets rather than raw local thigh angles; they remain a pose study, not production motion capture.
- `static/studio-tools.js`, `personas.py`: named local personas and read-only access to existing Open WebUI model presets. The bridge reads only model records, never auth/users/chats; no WebUI writes occur. Current source has two presets using uncensored-3b and no knowledge collections. Studio saves are private local copies. Referenced knowledge cannot silently bypass retrieval; those personas require a future authenticated WebUI chat adapter.
- Direct installed `uncensored-3b:latest` is the default answer model and is displayed below the stage. Saved personas are resolved server-side. Avatar movement acknowledgement is distinct from real-world tool claims.
- Blender 4.5.14 LTS and MPFB 2.0.18 were installed from official sources after SHA-256 verification. `character-tools-manifest.json` pins the downloads. An editable 54 MB workshop with the clothed sample, IK controls, ground/light setup and a separate hidden adult female MPFB base/Mixamo rig was actually built. `Open Character Workshop.command` opens it; the builder preserves an existing scene.
- Garment markers change separate mesh visibility at animation times. Imported production garments can declare `wardrobeSlot`/`wardrobeLabel`. The original sample coverage layer remains; this is not completed undressing/cloth physics or complete anatomy.

New tests include actual-rig IK lengths, grounded feet/hands during splits, hip-feedback stability, 30/60 fps interpolation, clip retargeting, blending, pause-aware wardrobe markers, alias negation, stale-load cancellation, persona persistence/read-only WebUI extraction, knowledge fail-closed handling and inert animation upload validation. Final automated results: 35 Python tests and 20 Node tests passed, plus all JavaScript syntax checks. Browser checks verified clip playback, loop/pause/resume, planted-foot hip controls, saved-persona persistence and direct uncensored-3b selection, a real greeting plus bow, and a waistcoat visibility cue firing at 1 second. The held-pose browser check exposed a Three.js property-mixer cache conflict with the idle pass; restoring the last desired clip pose before sampling fixed it, with a regression test. Fresh browser error/warning logs were empty. A real uploaded third-party animation and a production dressed/anatomical character remain unverified; no earlier declined character-upload test was retried.

See `CHARACTER_WORKSHOP.md` for the implementation, sources and production limits. The photographic adult character, full external detail, fitted underlayers/outfits, corrective body shapes and realistic dressing/recovery clips remain unfinished asset work. A small self-authored IK wave was baked from the local Blender workshop to the included 74 KB GLB and loaded/retargeted in tests. No MetaHuman/Mixamo account, agreement or downloaded professional clip was obtained.

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
