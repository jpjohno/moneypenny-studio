# Stable British voice identity

The saved Moneypenny voice remains Kokoro `bf_emma`; Jarvis remains `bm_george`, both with `en-gb` phonemisation. The saved owner preference and synthesis settings were not changed. The user reported a changed accent; the audit did not reproduce or acoustically diagnose that report.

A concrete consistency gap was fixed: streamed phrases previously looked up the mutable saved profile separately. Each new workspace reply now pins its selected profile and speed, and checks the returned provider, voice ID, profile and language before playing. Missing or mismatched metadata produces a clear error instead of playing another identity. The server reports a selected British voice as unavailable without substituting a cloud or browser voice. Stop ownership and explicit cloud alternative selection remain intact.

The local workspace Move & view menu also links to the animation builder. Public-host workspaces do not show that loopback link.

## Applying to the private broker

1. Match both private files to `VOICE_IDENTITY_BASES.json` before hashes. This patch is based on the current private workspace, including prior movement controls; it is not a replacement for the earlier release chain.
2. Review and apply `jjrvis-voice-identity.patch` from the broker directory, alongside the updated `voice_profiles.py` and mirrored focused tests.
3. Match after hashes. The patch was replayed against exact temporary copies and produced identical bytes.
4. Restart the broker and reload the workspace together. The new client expects identity metadata from the updated server. Runtime models, saved preferences and private credentials are not part of this overlay.

## Verification

53 focused Python tests and 21 JavaScript tests passed, covering British profile pinning, a saved profile changing between phrases, wrong/US voice metadata rejection, explicit missing-voice errors, Stop, stale audio events and the local-only animation link. Real synthesis through the updated in-process preview routes produced valid mono 24 kHz PCM WAV for both voices. The Moneypenny preview was byte-for-byte identical to the pre-fix live broker preview, confirming that this change did not alter its sound. Audio was not played or acoustically certified. See `VOICE_IDENTITY_VERIFICATION.json`. The coordinated Studio/broker restart and workspace reload were completed locally. After the owner unlocked JJRVIS, its updated movement menu and animation-builder link were visibly verified. The microphone was left off; this verifies activation, not acoustic quality.
