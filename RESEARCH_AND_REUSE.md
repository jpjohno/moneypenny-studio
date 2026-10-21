# Existing work and free production route

Inspected on 18 October 2026. Only accessible chats, repositories and local files can be reviewed; this is not a claim of access to every historical ChatGPT conversation.

## Existing work inspected

| Work | What was found | Decision |
| --- | --- | --- |
| Original `jpjohno/moneypenny-studio` at `8101744` | One Flask file, portrait CSS transforms, browser speech, one-turn Ollama `/api/generate`. No 3D mesh, rig, mouth shapes or speech waveform access. | Preserve the local Flask/Ollama concept; replace the display and conversation pipeline. Keep `/chat` as a supported integration URL with validated input and explicit errors. |
| JJRVIS communication workspace and the accessible “Build communication broker” chat | Installed Ollama models; the approved local `bf_emma` British Kokoro voice; local Vosk dictation; prior interruption and review work. | Reuse the installed voice environment/weights and listening environment. New studio owns its own worker. Answer model and voice remain independent. No trading or communication-send routes are connected. |
| Enki Sticker Studio, October 2026 | Local FFmpeg/Pillow pipeline for timing, segmentation, premultiplied alpha, framing and transparent WebP export. Read the source and README. | Useful for future prerecorded reaction clips, transparent overlays or export tooling. It does not supply a humanoid rig, facial blend shapes or a live conversation renderer. Private source videos were not copied into this public project. |
| `prepared_project_enkidu/render_enkidu.py` | MoviePy compositor combining pre-generated frames, cuts and a narration track. It can substitute colour clips when frames are missing. | Useful for edited presentation/video export. It cannot turn the existing frames into an interactive 3D human. None of its placeholder generation is used in the live studio. |
| Existing `enkidu3d` / `sadtalker` Python environments | Local environment directories were found. | Presence of an environment does not verify usable weights, acceleration, quality or a running service. They are not labelled as connected or working here. |

Machine-specific paths are in the ignored `.runtime/machine.json` and the local handover copy; credentials and personal source media are excluded from Git.

## Free stack chosen and implemented

**Three.js + TalkingHead + HeadAudio + Ollama + Kokoro + Silero VAD + whisper.cpp (Vosk fallback).** This runs the 3D stage and mouth analysis in the browser, with inference and speech on the Mac. Each generated audio phrase drives mouth shapes directly, while the next phrase is prepared. This avoids trying to extract waveform/timing from browser `speechSynthesis`, which does not expose them in a reliable cross-browser way.

[TalkingHead](https://github.com/met4citizen/TalkingHead) supplies rigged body motion, eye contact, expressions and gesture templates. [HeadAudio](https://github.com/met4citizen/HeadAudio) supplies audio-driven visemes locally. Its authors explicitly describe the accuracy trade-off: the real-time audio classifier is approximate and can be less accurate than good timed phoneme data. It is useful here because the existing Kokoro ONNX path returns a WAV without phoneme timestamps.

No model-provider billing is used. Downloads, local storage, CPU/GPU use and normal hardware/electricity costs still apply. The current voice system preserves identity and natural phrasing but does not offer arbitrary emotional voice acting. “Playful” changes language and visible performance; it does not guarantee a newly trained expressive voice.

## Character production

The current studio uses the upstream MPFB character because its stated licence is CC0. It has a proper skeleton and mouth shapes. The original outfit is retained as coverage, with separate prototype skinned skirts, waistcoat and footwear added. These simple meshes do not meet the requested professional clothing or photographic asset standard.

For a bespoke professional person, use [Blender](https://www.blender.org/) and [MPFB](https://static.makehumancommunity.org/mpfb.html). They provide a free authoring route. The [TalkingHead MPFB guide](https://github.com/met4citizen/TalkingHead/blob/main/blender/MPFB/MPFB.md) covers the compatible rig, facial shape keys, poses and GLB export. A recognisable likeness still requires modelling, suitable references, hair/clothing work and visual review. A single photograph does not establish the back/side geometry or supply an animation rig.

Keep identity, voice, rig, clothes, personality and motion as separate assets/settings. That allows the same person to be office-like, warmer or more playful without replacing the underlying character or accidentally changing the approved voice.

## Alternatives researched

| Tool | Useful role | Practical limit for this request |
| --- | --- | --- |
| [VRoid Studio](https://vroid.com/en/studio) / [three-vrm](https://github.com/pixiv/three-vrm) | Free stylised character route with a structured avatar format. | A different runtime/retargeting route; VRM import is not implemented in this studio. |
| [LivePortrait](https://github.com/KlingAIResearch/LivePortrait) | Animate a portrait for a photographic talking-head/video treatment. | Portrait animation is not a freely rotatable rigged 3D person. Weights, hardware and dependencies need separate validation; no LivePortrait service was installed or represented as live. |
| [HeadTTS](https://github.com/met4citizen/HeadTTS) | Kokoro-based TTS with phoneme/viseme timestamps; a promising route to more precise mouth timing. | Not integrated or benchmarked here. Replacing the existing speech runtime should preserve `bf_emma`, compare pronunciation and latency, and then validate audio/viseme alignment. |
| Photo-to-avatar web services listed in TalkingHead's guide | Potential shortcut to a recognisable head. | Free tiers, commercial rights and permission to distribute downloadable web assets vary. No account was created and no portrait was uploaded. The current path does not depend on one. |

## Next meaningful improvements

1. Author and approve an original Moneypenny character with polished hair, skin, clothing and facial shapes. Import and review it from multiple angles and during speech.
2. Benchmark the fixed British voice with phoneme timestamps (for example HeadTTS), then compare to current audio-derived lips without changing identity silently.
3. Phrase buffering, synthesis prefetch and persistent live listening are now implemented. Finish actual human acoustic interruption testing and compare measured cold/warm latency.
4. Add individually scoped assistant adapters. Keep file access, mail drafts and other consequential actions behind their own explicit review controls. This studio currently generates conversation only.

The implemented application is a working local foundation. A photoreal bespoke person, fully expressive vocal acting, background actions and public multi-user hosting remain separate work, not completed features.

## Live conversation upgrade

The existing Jarvis streaming/cancellation patterns informed the separate studio implementation. [vad-web](https://github.com/ricky0123/vad) runs [Silero VAD](https://github.com/snakers4/silero-vad) locally; [whisper.cpp](https://github.com/ggml-org/whisper.cpp) owns a private warm loopback transcription worker. Speech chunks begin during answer generation. The body director and prototype wardrobe stay separate from that voice path. See `SESSION_HANDOFF.md` for measured verification and remaining limitations.
