# Moneypenny Studio handover

Updated: 18 October 2026. Local checkout: `/Users/jamesjohnston/Documents/Moneypenny-Studio`. Source: `jpjohno/moneypenny-studio`, branch `codex/live-3d-persona`, based on `810174485124cfe67f01c4804790eabdc355bba5`.

## Implemented

- Flask app split into template, responsive CSS, browser controller and local speech workers.
- Actual TalkingHead rigged 3D human with blinking, idle motion, gaze, facial mood, gestures, camera controls and sample wardrobe styling.
- Imported GLB container/embedded-asset/basic-rig validation, renderer compatibility checks, browser IndexedDB retention. Portraits are explicitly references only.
- Installed Ollama model discovery, `/api/chat/stream` NDJSON, real conversation context, token limit handling, bounded input, timeout/errors; legacy `/chat` retained.
- Independent fixed British `bf_emma` voice through a private resident Kokoro subprocess. Full reply is rendered once, then played continuously. Existing JJRVIS environment and model files are reused read-only.
- HeadAudio browser worklet/classifier drives 15 Oculus mouth shapes from that exact audio, with 80 ms output delay.
- Expression/action response: smiles/mood, nod, lean, tilt, wink and selected hand gestures. Movement intensity can be adjusted. Performance begins with speech playback.
- Explicit microphone recording, local Vosk transcription, composer review before sending, 29-second recording limit, stop/cancel handling. No audio recording retained by the application.
- Per-turn cancellation IDs, late voice request rejection, browser abort/source teardown, independent ownership across tabs.
- Persona settings export/import, local browser persistence, one-click Mac launcher, pinned assets/Three.js and included vendor licences.
- Loopback-only server, Host/Origin/custom-header protection, local asset CSP, bounded requests and no-store audio/chat responses.

## Files

| Path | Purpose |
| --- | --- |
| `app.py` | Local HTTP routes, input checks, Ollama streaming and parsing |
| `speech.py` | Voice process ownership, framing, cancellation and transcription invocation |
| `speech_worker.py` | Kokoro synthesis, voice model checksum checks, fixed `bf_emma` |
| `transcribe_worker.py` | Bounded Vosk transcription subprocess |
| `templates/index.html` | Studio UI |
| `static/studio.js` | Character, audio, turn lifecycle, chat and persona controls |
| `static/recorder.js`, `static/record-worklet.js` | Explicit microphone capture and WAV conversion |
| `scripts/setup.py` | Pinned asset download and voice reuse/optional independent setup |
| `scripts/launch.py`, `Start-Moneypenny.command` | Existing-instance check and local launch |
| `tests/test_studio.py` | Request/history/error/stream/cancel/input protection tests |
| `assets-manifest.json` | Upstream URLs and SHA-256 for vendor files and sample GLB |

## Verified live on this Mac

- `/api/status`: real installed Ollama catalogue, existing voice files, existing Vosk model and sample avatar detected.
- Ollama `/chat`: actual `MoneyPenny:latest` reply completed in 6.96 seconds for a brief introduction (includes local model loading; not a latency guarantee).
- Kokoro: actual 24 kHz mono PCM WAV generated in 3.07 seconds; 156,524 bytes and 3.26 seconds of spoken audio for the short test phrase.
- Generated voice resampled and sent to the actual local Vosk route: HTTP 200 in 1.25 seconds, recognising “hello james shall we make something rather good together”. This verifies the audio/transcription pipeline, not physical microphone permission or ambient recording quality.
- Backend tests: 21 passed. JavaScript syntax checks passed. Asset setup ran successfully using existing JJRVIS files.
- Browser: actual 3D geometry rendered; live preview reached Speaking; lighting/framing inspected. See the final acceptance note below for further completed interactions.

## Final acceptance note

- Browser conversation: told the assistant the test favourite colour was green; the next turn asked for it and the actual model answered “Green”. This exercised the real UI, streamed reply and history path.
- Browser: voice preview entered Preparing her voice, then Speaking; Stop returned to Here with you and re-enabled conversation. Wardrobe and professional personality controls changed successfully. Default narrow/mobile and desktop layouts were inspected.
- Browser after a fresh load: stopping an in-progress model reply immediately displayed “Reply stopped.” and restored the controls. An overflow caused by visually hidden file-input widths was found and corrected.
- Live server: active speech cancellation returned 204 and the cancelled render returned 400; a deliberately late cancelled turn returned 400; a fresh turn then returned a valid 57,612-byte WAV. These were real local worker requests.
- Character upload acceptance was blocked by the browser approval system because file-upload permission was declined. No alternative upload route was attempted. The import implementation and static compatibility checks exist, but successful UI import/persistence remain unverified.
- Local screenshots are saved at `verification/studio-desktop.jpg`, `verification/studio-conversation.jpg` and `verification/studio-playback.jpg`. The playback capture shows the actual Speaking state, raised hand and open mouth during the continuous WAV. They are ignored by Git. Earlier browser console errors from a now-corrected WASM CSP and a template-refresh mismatch are retained in the browser's historical logs; they should not be confused with fresh-load errors.

## Limits and continuation

- Current asset is a CC0 sample; no bespoke Moneypenny likeness was created. Existing portrait/media files were not published or used to claim a new rig.
- Mouth shapes use approximate audio classification. Perfect film-level phoneme alignment is not claimed.
- Speech starts after generation and synthesis. One continuous utterance avoids sentence-join gaps but adds a pause. No full-duplex or streaming speech synthesis yet.
- Mic permissions/physical device capture and human audible quality acceptance must be tested by the user. The local transcription route has been exercised with generated audio.
- Own-voice setup download URLs were checked, but a fresh independent environment on a second machine has not been verified.
- GLB import is for TalkingHead-compatible rigs. No VRM runtime, automatic photo-to-rig process, outfit geometry generator or character-training pipeline.
- No app actions, broker-send integration, trading integration, cloud synchronisation or public production hosting.
- The local Flask process runs only while launched. The command launcher is the durable way to reopen it; no new LaunchAgent was installed.
- Personal media, conversation data, machine paths, environments, downloaded avatar and test artifacts are excluded from public source commits.

## Existing local references (read-only)

- JJRVIS broker folder: `/Users/jamesjohnston/.codex/.chatgpt-projects/g-p-695eea173370819196be0c9be135bb6e/outputs/communication_broker`.
- Enki Sticker Studio source: `/Users/jamesjohnston/Documents/Codex/2026-10-10/referenced-chatgpt-conversation-this-is-an-2/outputs/Enki-Sticker-Studio-GitHub`.
- Earlier Enkidu video compositor: `/Users/jamesjohnston/Downloads/prepared_project_enkidu/render_enkidu.py`.

These are references, not copied personal assets or published services. The local `.runtime/machine.json` contains the actual environment/model paths and is ignored by Git.
