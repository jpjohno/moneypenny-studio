# Voice timing and surface response

Generated Kokoro speech now carries its existing phoneme durations in one optional, bounded MPVS WAV chunk. The voice, synthesis settings and PCM samples are preserved. The chunk contains only time spans and the 15 allowlisted mouth-shape names, with no original text or executable instructions. No extra model, inference pass, dependency, recording or rendering loop is added.

Studio parses timing before Web Audio can detach the bytes. It validates duration against the decoded PCM, clips cues when the existing quiet-tail trim is certain, and schedules mouth shapes on the same audio clock and output delay. Adjacent phrases retain the preceding delayed mouth performance. Stop releases all queued targets and stale decode completion cannot revive an old reply. Timing slider changes follow the live delay value without accumulating drift. WAVs with absent or invalid metadata retain the HeadAudio fallback.

Random lip rolls, presses and stretches previously remained under speech and could pull a closed consonant apart. These random channels and the resting smile now yield during speech and its short output drain; explicit fixed, realtime and named expression controls keep ownership.

Skin and blouse now use the existing shared room environment explicitly. This fixes Three r180 overriding their per-material reflection strength with the scene default. The milder response reduces washed-out skin and fabric; eyes, hair textures, body geometry and face shapes are not changed. The room texture remains scene-owned. The current source still looks CG and is not a photographic asset.

## Existing private JJRVIS installation

Apply jjrvis-phoneme-timing.patch only when the three before hashes match PHONEME_TIMING_BASES.json. Copy speech_timing.py beside local_voice_worker.py. The mirrored local_voice.py, local_voice_worker.py and presence_proxy.py are included. The cache version changes to 4 so earlier plain-WAV cache entries do not conceal the new metadata; existing cache files are retained. Use the matching updated Studio static source, including speech-timing.js. Restart Studio and the existing broker, then reload the Mac app content; no native rebuild or private unlock change is needed.

The selected saved Studio personality has a separate exact overlay and follow-up routing patch; see STUDIO_PERSONA_RELEASE.md and PERSONA_ROUTING_RELEASE.md. Persona text, preferences, credentials, complete private broker sources, recordings and generated binaries are not part of this source handover. PERSONA_PHONEME_VERIFICATION.json records the actual test and live scope.
