# Moneypenny Studio

A local 3D conversation studio: a rigged human character with idle movement, blinking, eye contact, expressions, hand gestures and mouth shapes driven by the actual British voice recording. Ollama answers, Kokoro speaks and Whisper transcribes on your computer (with a Vosk fallback). No paid API or cloud account is required for the implemented path.

The combined working version is on **`codex/live-3d-persona`**, in [PR #1](https://github.com/jpjohno/moneypenny-studio/pull/1). Open **Moneypenny.code-workspace** in VS Code for the complete web app and Blender tools. The separate Desktop checkout is preserved; its `app.py` is a Blender script, not the web server. See the latest section of [SESSION_HANDOFF.md](SESSION_HANDOFF.md) before continuing development.

For the VS Code coding assistant, **Dolphin Llama 3 - Local** (`cognitivecomputations/dolphin-llama3:latest`) is selected in Continue's safer Chat mode after the 3B model invented files and destructive commands instead of reading the workspace. **Uncensored 3B - Local** (`uncensored-3b:latest`) remains installed and shares the same model digest as `sadiq-bd/llama3.2-3b-uncensored:latest`; no extra download is needed. Both configurations now direct the model to the real source map in [.continue/rules/moneypenny.md](.continue/rules/moneypenny.md). The active configuration is `~/.continue/config.yaml`, not the deprecated JSON file; keep Python source out of that YAML. A reproducible configuration is in [config/continue-local.example.yaml](config/continue-local.example.yaml). The Dolphin model rejects Ollama's native tool API, so Continue's **Settings → Experimental → Only use system message tools** must be enabled for its Agent mode. This compatibility route does not make an 8B model reliable at arbitrary coding tasks: use Chat for planning, switch to Agent only for a narrow reviewed edit, inspect every diff and run checks. File edits are accepted through Continue's normal review buttons. In this installed Continue version, `read_file` accepts absolute or relative paths, while `single_find_and_replace` requires a workspace-relative path.

To dictate a request, focus Continue's input and use VS Code's native **Edit → Start Dictation**, then submit the text. Dictation is already available on this Mac; this setup did not start a microphone recording or verify acoustic transcription quality. Do not confuse VS Code's separate built-in chat pane with Continue. This is a local Mac connection, not a deployment on the trading VPS.

Dolphin is retained at the user’s request. The optional Qwen download was removed; it is not required by this setup. Dolphin’s publisher describes it as uncensored, which does not guarantee arbitrary request compliance or coding accuracy.

For editing existing code with this Dolphin model, open the file, select the relevant code and press **⌘I** to enter Continue's **Edit** workflow. Enter or dictate the requested change, submit it, inspect the actual inline diff and accept it if correct. Agent mode can call real tools through the compatibility option, but ordinary requests still sometimes produce only snippets or invalid tool calls in testing. The connection repair does not resolve those model-quality limits.

**Open Studio Rig Controls.command** locates Blender on this Mac and opens the local dressed performance source with a **Moneypenny** sidebar. Remember a pose, edit a different pose, then animate back to the remembered pose. A new timeline action keeps the previous action available; constrained rigs must be animated through their own controls. Export movement produces a motion-only GLB for **Motion library → Add animation** in the web app. No character upload or automatic execution of model-written code is involved. See [CHARACTER_WORKSHOP.md](CHARACTER_WORKSHOP.md#blender-to-web-studio-motion-workflow).

## Character handover and 4D workshop

Read [GEMINI_HANDOFF.md](GEMINI_HANDOFF.md) before continuing the character rebuild. The original **Moneypenny-Adult-Body-Source.blend** is now included at repository root as an unfinished adult authoring base. **Open Moneypenny Body Source.command** opens it in Blender. **Open 4D Capture Workshop.command** opens the prepared local recorded capture; it is a playback/authoring workshop, not a scanner for creating a new person. Both launchers preserve existing Blender windows and disable embedded source scripts.

Publication correction: a separate root-level **Moneypenny-Adult-Anatomy-Study-v3.blend** was already tracked earlier and differs from the runtime copy. The original parametric base is the preferred clean starting point. Newer runtime exports and Renderpeople capture data remain local; their distribution is not covered by publishing the original base. See [CHARACTER_SOURCE_PROVENANCE.json](CHARACTER_SOURCE_PROVENANCE.json) for hashes, component licences and actual scope.

## JJRVIS front of house

Open the combined private workspace at http://127.0.0.1:8766/workspace . The existing JJRVIS service must be running separately. Moneypenny and the interactive device atlas share one scene; **Customise Moneypenny** opens this full studio. The embedded view has transparent surroundings and uses the local voice with speech-driven mouth shapes. The current v38 character improves the hair fringe, brow fit, portrait lighting and natural idle motion, following the hand and blouse-fit corrections. It remains a CG character, not a photographic asset.

## Captured human previews

Open **Realism previews** in the studio header, or http://127.0.0.1:8090/realism on the prepared Mac. **Recorded 4D** plays a real captured performance with camera rotation, play/pause and a timeline. The complete local review is 556 independent mesh frames at 15 fps, about 37 seconds, with only three decoded frames retained. **Clearer detail** uses 1024px captured textures; **Lighter playback** uses 512px textures. Its changing topology is evaluated independently for each frame. **Scanned character** is a separate rig and expression study with wave, mouth and blink controls.

These private candidates do not replace the current conversational character. Recorded motion cannot generate new requested actions; the scanned speech controls are approximate and have not passed live pronunciation acceptance. Source assets are not in Git and are unavailable on a fresh checkout until prepared locally. The vendor's third-party app/SaaS restrictions require separate clearance before customer distribution. See [the review release and actual verification](integrations/jjrvis/SCANNED_4D_REVIEW_RELEASE.md).

The integration patch and connection-status helper are in [integrations/jjrvis](integrations/jjrvis/README.md). They apply to James's existing JJRVIS package; this repository does not become a standalone JJRVIS installation. Runtime, credentials, private source records and generated large character binaries are not included. The [private concierge product strategy](integrations/jjrvis/PRODUCT_STRATEGY.md) separates implemented features from proposed phone, home, camera, car and household work.

In the embedded view, autonomous idle movement stays local; background choreography does not independently load another Ollama model. Speech is prepared in bounded passages, and playback messages are tied to each reply so Stop and stale completion remain separate. `/api/status?quick=1` checks stage/voice prerequisites without waiting for an Ollama catalogue request. Application tests live under `tests/`; the integration tests need the existing JJRVIS environment.

## Open on this Mac

Double-click **Start-Moneypenny.command**, or run:

```sh
/Users/jamesjohnston/Documents/Moneypenny-Studio/Start-Moneypenny.command
```

The studio opens at **http://127.0.0.1:8090**. On macOS, its default launcher installs a private login service that starts after login and survives closing Terminal. It binds only to this Mac and uses Waitress. The launcher checks for an existing studio and never stops another application occupying the port. Private logs are in `~/Library/Logs/Moneypenny-Studio/`; configuration recovery copies stay in `.runtime/service/`. To inspect or stop this service, run `./Manage-Moneypenny-Service.command status` or `./Manage-Moneypenny-Service.command stop`; `start` enables it again and `remove` removes its login entry while retaining a recovery copy. To run a temporary foreground instance on a different port:

```sh
MONEYPENNY_PORT=8091 ./Start-Moneypenny.command
```

Requirements: macOS or Linux, Python 3.10+, Node.js/npm for installing the pinned Three.js dependency, a modern WebGL2 browser and [Ollama](https://ollama.com/). Start Ollama and install an answer model. The studio discovers installed models rather than inventing a catalogue. On James's Mac `cognitivecomputations/dolphin-llama3:latest` is installed and selected for the saved Moneypenny persona. Fresh settings prefer that installed tag; existing saved model choices are respected. No model is downloaded automatically.

## First installation elsewhere

```sh
git clone --branch codex/live-3d-persona https://github.com/jpjohno/moneypenny-studio.git
cd moneypenny-studio
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm ci --ignore-scripts --cache .runtime/npm-cache
.venv/bin/python scripts/setup.py
.venv/bin/python scripts/setup.py --voice
./Start-Moneypenny.command
```

The default character download is about 37 MB. Independent voice/listening setup downloads several hundred MB and creates `.voice-venv/` and `.runtime/` inside this checkout. Python packages come from PyPI; speech weights come from the Kokoro ONNX release and Vosk's official model server. Initial setup needs internet access. Normal chat, speech, dictation and rendering use loopback/local assets. A fresh independent `--voice` installation has not been end-to-end tested on a second machine; existing-runtime reuse was verified on this Mac.

If JJRVIS's existing British voice runtime is present, `scripts/setup.py` reuses its Python environment and model files **read-only**. It starts a separate voice worker and does not call, stop, change preferences in, or take over the JJRVIS broker. You can explicitly select its folder:

```sh
.venv/bin/python scripts/setup.py --link-jjrvis /absolute/path/to/communication_broker
```

## Use the studio

- Choose Moneypenny, Professional, Companion or Playful, or edit the personality directly. Give the character another name if desired.
- Adjust body language, expression, studio outfit and portrait/upper-body/full-body framing. Drag the character to change the viewing angle; the framing buttons control the camera.
- Click **Preview voice & movement**. Replies begin from a ready phrase while the rest of the answer is still being generated. The next audio is prepared during playback; HeadAudio analyses the exact audio to drive mouth shapes, with an 80 ms output delay to offset processing latency.
- Press **Start live conversation** once to open the microphone after permission. It stays open between turns, detects speech locally, interrupts old playback on speech onset and automatically submits each transcribed turn after a pause. **Stop live conversation** closes it. **Record note** remains a separate review-before-send option.
- **Stop** cancels the active browser turn, stops sound, resets mouth movement, and terminates that turn's own voice render. Late speech requests carry a cancelled turn ID and are rejected. Another tab's voice render is not cancelled.
- Change the answer model independently from the voice. The British `bf_emma` identity stays fixed; speed is adjustable from 0.8× to 1.5×.
- Export/import persona JSON to save personality, movement, wardrobe and voice settings. Imported GLBs are retained in this browser's IndexedDB. Conversations are kept in page memory and disappear on reload/new conversation. The studio sends up to the most recent 20 messages back to Ollama.

Speech is generated in phrase chunks, rather than waiting for the entire reply. There is still model/synthesis latency, especially on the first cold request. It is a local turn-based conversation with speech-onset interruption, not an end-to-end speech-to-speech model. Acoustic echo and interruption quality need actual speaker/microphone acceptance testing. Local model answers may be unreliable; this version has no file, messaging, trading or other action tools.

## Live follow-ups and movement

Say “be quiet”, “be quiet for ten minutes”, “resume”, or “ask me in ten minutes”. Follow-ups are stored in `.runtime/reminders.sqlite3`; a visible open studio tab claims a due follow-up when the character is free to respond. A closed tab or sleeping Mac cannot deliver it until the studio is available again.

Independent movement has its own persona, activity level and toggle. Local procedural choices run by default; model-generated original choreography is an optional toggle because it shares the conversation model and can delay replies. It can choose movement without a chat command, compose body skills, request a local-model plan or run validated custom joint keyframes. Direct instructions include reach targets, a jig/dance, walking, turning, sitting, kneeling, lying on the back, stretching, bowing and splits. These are procedural prototype motions with IK for reach targets; production clips, collision constraints and realistic transitions are still needed.

Supported movement commands now execute directly from chat instead of depending on the language model's agreement. Try **“Bend over”** or **“Turn around and bend over”**. The clothed forward-bend study plants both feet and eases upright again; directed turns keep their direction across following steps. A second turn faces the other way. Direct instructions take priority over conversational gestures. Pure action requests display **Local action · no model wait**; mixed questions still use the conversation engine. This command routing does not supply animations for every possible request.

The wardrobe now adds separate skinned waistcoat/skirt/dress-skirt meshes and prototype footwear. The original outfit remains as a coverage layer. This is not a completed anatomical body, cloth simulation or realistic undressing system. See [PHOTOREAL_CHARACTER_SPEC.md](PHOTOREAL_CHARACTER_SPEC.md) and the proposed [BUSINESS_PLAN.md](BUSINESS_PLAN.md).

The separate local **Open Performance Character.command** opens a dressed Blender source with facial speech/expression shapes, skin maps, individual hair strands, fitted office clothes/shoes and moderate elbow/knee volume correctives. The studio prefers the local clothed `Moneypenny-Style-v26.glb` styling revision when available, with validated reviewed-free, v9, v6 and bundled-sample fallbacks. It preserves the authored shoulder rest pose, adds gentle breathing, reduces the over-large v25 profile, refits the blouse, and uses a loose CC0 bob with blonde colour variation. The free v10–v16 face/body prototypes were not promoted after visual review. The new fictional face/body and its build chain are documented in CHARACTER_WORKSHOP.md; a source upgrade is not a photographic-quality guarantee. The v9 study adds spatial roughness, multiscale skin normals, a 12,000-strand scalp groom and expression-linked brow filaments. These are authored/procedural assets, not photographic scans. An incompatible candidate fails back to the CC0 sample without replacing the saved source. It still looks computer-generated; photographic realism, commercial redistribution clearance and unrestricted motion remain unfinished until live visual, speech and motion acceptance pass. See [CHARACTER_WORKSHOP.md](CHARACTER_WORKSHOP.md) for build steps, licence limits and actual verification. **Independent movement → Foot on seat** previews a clothed supported-step study on either side; Stop lowers the foot. Intimate hygiene is not animated.

All implementation/build scripts and the handover are in Git. Generated character scenes, model weights and private runtime data remain local. [LOCAL_CHARACTER_ASSETS.json](LOCAL_CHARACTER_ASSETS.json) records paths, sizes and checksums of the saved character deliverables; run `scripts/character/inventory_local_assets.py` after saving refinements to refresh it. Unsaved Blender edits are not part of those saved-file checksums. **Base clothes · hide added layers** hides only added garments and preserves the fixed sample outfit's appearance.

For higher-quality local transcription on a Mac with whisper.cpp:

```sh
brew install whisper-cpp
.venv/bin/python scripts/setup.py --whisper
```

The pinned `base.en` model is about 148 MB. The studio starts its own loopback Whisper server and keeps it warm. On this Mac the existing whisper.cpp install was reused.

## Motion library, rig and character workshop

The studio now has saved/imported GLB/BVH animation clips, crossfades, speed/loop/pause controls, named movement words, bone mapping, draggable hand/foot/hip targets and foot planting. Clothing visibility can follow markers in an authored dressing animation. Named personas can be saved here or loaded from the existing local Open WebUI model catalogue, with `uncensored-3b:latest` selected directly by default.

On this Mac, Blender 4.5 LTS and MPFB are installed, with an editable character workshop and a separate unfinished adult body source. Double-click **Open Character Workshop.command**. See [CHARACTER_WORKSHOP.md](CHARACTER_WORKSHOP.md) for usage, formats, rig controls, source status and the distinction between the implemented library and unfinished photographic/body/clothing assets.

**Open Body Editor.command** opens the separate editable adult base, with actual MPFB body-shape controls and initial skin development. **Set Up NVIDIA Motion.command** and **Generate NVIDIA Motion.command** prepare and run genuine ARDY offline motion generation. The native Mac core is installed and its checkpoint loads on CPU; required text-model access and full generation remain unverified. See [NVIDIA_MOTION.md](NVIDIA_MOTION.md) for the measured tests and remaining setup.

## Bring in your own person

Use **Import 3D character** with a self-contained GLB 2.0 file under 80 MB. The renderer expects a TalkingHead-compatible, Mixamo-style humanoid rig and Oculus mouth shapes (including `viseme_aa` and `viseme_PP`), plus facial shapes for the supported expressions. It validates the container, embedded assets and basic rig/shapes before loading. A complete compatibility check occurs during loading. VRM and arbitrary unrigged meshes are not supported by this import.

**A reference photograph does not automatically become a 3D likeness.** The portrait control is a visual reference only. The bundled character is a CC0 sample, not a finished bespoke or photorealistic Moneypenny. For an original free character, use Blender + MPFB, build the face/hair/clothes, export the TalkingHead rig and shapes, and import the resulting GLB. See [RESEARCH_AND_REUSE.md](RESEARCH_AND_REUSE.md) for the free tools and existing work that were inspected.

## Create and replay animations

Open **Move & view → Create animations** in the local JJRVIS workspace, or open
http://127.0.0.1:8090/?panel=animation#animationBuilder .

1. Name the animation and add movements such as Wave, Bow, Stretch, Turn or Dance.
2. Change their order, duration and waving hand. A sequence holds up to eight steps.
3. Use Preview and Stop to review the actual character, then Save animation.
4. Reopen it under Open a saved animation; Export JSON/Open JSON transfers the
   editable sequence. Save again creates another library item so the original remains.

The builder uses the existing local body controller and makes no language-model
request. Sequence playback supports Play/Stop and speed; pause, timeline seeking
and clothing cues apply to imported/baked clips. Blender remains the separate
free authoring tool for new mesh, rig and captured-motion work. The builder does
not invent arbitrary realistic motion or turn the current CG asset into a scan.

Appearance choices are shared with JJRVIS. Light blonde and Brighter blue can be
changed back in Character & appearance; the iris adjustment preserves pupils,
eye whites and the original eye texture. Voice & engine keeps the local British
Moneypenny voice. The JJRVIS integration now pins voice identity for each reply
instead of re-reading mutable settings for every phrase.

## Verification

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
npm run check
npm test
```

See [SESSION_HANDOFF.md](SESSION_HANDOFF.md) for measured live checks, browser acceptance, limitations and the exact source map. Test recordings and browser screenshots are local-only in ignored files; no personal media is shipped to the public repository.

## Components and licences

- [Three.js](https://github.com/mrdoob/three.js), MIT; pinned in `package-lock.json`.
- [TalkingHead](https://github.com/met4citizen/TalkingHead), MIT; pinned upstream commit in `assets-manifest.json`; licence included alongside vendored modules.
- [HeadAudio](https://github.com/met4citizen/HeadAudio), MIT; pinned upstream commit, included model and licence. Audio-derived mouth shapes are approximate, not perfect phoneme alignment.
- Studio character: upstream `TalkingHead/avatars/mpfb.glb`, [CC0 per upstream attribution](https://github.com/met4citizen/TalkingHead#license). Downloaded by setup, SHA-256 verified, excluded from source Git history.
- [Kokoro ONNX](https://github.com/thewh1teagle/kokoro-onnx), MIT implementation; [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M), Apache-2.0 model. Voice model files are checksum-verified before use.
- [Silero VAD](https://github.com/snakers4/silero-vad) through [vad-web](https://github.com/ricky0123/vad): local speech detection; dependencies pinned in the lockfile.
- [whisper.cpp](https://github.com/ggml-org/whisper.cpp): local warm transcription with the pinned English base model.
- [Vosk](https://alphacephei.com/vosk/), Apache-2.0 implementation; the selected `vosk-model-small-en-us-0.15` is listed as Apache-2.0 on its [model page](https://alphacephei.com/vosk/models).

Keep licence terms for any character, clothing, textures or voice you add. The shipped path deliberately uses the CC0 MPFB character rather than upstream's non-commercial sample characters.

The server binds to loopback, rejects foreign Host/Origin requests, requires the studio's custom request header for POST actions and disables response caching for chat/audio. It is a single-user local tool. Public hosting, user accounts, remote microphones and a hardened multi-user deployment are not implemented.
