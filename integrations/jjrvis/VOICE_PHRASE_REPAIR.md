# Phrase completion and fabric repair — 20 October 2026

The owner reported that the spoken map command did nothing. A listening indicator alone was not a successful speech-to-action acceptance test.

The Apple bridge now completes partial recognition after 1.4 seconds without changed words, forwards one final phrase and stops that recognition session. Abort and permission errors discard pending words; late results cannot double-submit. Native microphone input levels are forwarded at a bounded rate, and the workspace shows Hearing text on interim results. On-device recognition remains required; no new cloud speech destination was enabled.

Apply jjrvis-voice-phrase.patch after jjrvis-conversation-ux.patch with the recorded exact workspace.js hash, then copy native/apple/JJRVISApp.swift and the phrase tests. The Mac build compiled, was development-signed and installed. Its restart requires the owner to unlock again. The new spoken microphone-to-action round trip is pending the owner test; it is not marked passed. The typed show my map action opened the map and queued its spoken acknowledgement in a live browser test.

The clothed v30 runtime asset relaxes square fabric impressions in the blouse and regenerates its normals. Body and facial shape keys are unchanged. scripts/character/refine_blouse_v30.py reproduces the new export from the preserved v29 local GLB and refuses to overwrite it. It adjusted 2978 fabric vertices. The running browser showed rounded fabric instead of the broad rectangular impressions. This is a clothing correction, not a nude anatomy edit or a photorealism claim. The original exports remain intact; binary character assets remain outside Git.

Validation: 16 targeted voice tests passed, including partial-phrase completion, timer replacement, abort, permission errors and explicit Finish. Studio API suite: 42 passed. No new service permissions, household credentials, payments, trades or outbound messages were created.
