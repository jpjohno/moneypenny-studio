# Voice request routing and Stop status

The typed request “For a voice check, say exactly: A calm afternoon at home.” previously matched the fixed microphone FAQ merely because it contained “voice”. Voice help now requires an actual control, listening or microphone problem question. Quoted questions remain normal answer requests. An anchored top-level “say exactly: TEXT” or “For a voice check, say exactly: TEXT” now returns the bounded literal text directly as a local speech utility, with no model call or device dispatch. Payloads must contain 1–400 characters; existing credential redaction still applies. Embedded instructions inside a larger explanation or quotation do not activate it. Genuine microphone-help questions retain the existing deterministic answer. No other intent routes, answer providers or microphone permissions were changed.

Stop now restores the ready character badge immediately. Previously, Stop discarded pending speech ownership and its late idle acknowledgement, leaving the old SPEAKING text visible. Unowned frame events can no longer resurrect that label.

## Private broker overlay

Apply after the voice-identity increment only when the two private files match the exact before hashes in `VOICE_HELP_BASES.json`. Review and apply `jjrvis-voice-help.patch`, copy the two mirrored focused tests into the existing broker tests directory, then check the after hashes. Full owner source, runtime data and credentials remain excluded. The new intent tests reuse the receiving broker's existing `test_core.py` fixture.

89 Python intent/Core/stream tests and 21 JavaScript presence/startup/interrupt checks passed. The patch was applied to temporary exact source copies and reproduced the final files. Restart the broker and reload JJRVIS together before checking the installed app. This overlay does not establish native activation or auditory acceptance by itself.

The local broker restart was completed on 21 October. In the already-unlocked
installed Mac app, the exact request returned “A calm afternoon at home.”,
Replay reached Speaking, and Stop returned the character badge to 3D READY.
The microphone remained off. This confirms activation and playback state,
without certifying acoustic quality or exact phoneme alignment.
