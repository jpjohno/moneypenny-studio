# Mac capture and successful spoken-map acceptance — 20 October 2026

The owner twice reported microphone activity without a reply. The Mac now uses the existing browser PCM capture and configured transcription endpoint instead of preferring the unproven Apple recognition bridge. The selected provider is preserved; cloud transcription can still be configured. This is not an all-offline claim.

Audio is converted from the AudioContext's actual rate to the decoder's 16 kHz PCM contract, with phase preserved across callbacks. Previously it assumed the requested 16 kHz rate was always honoured. Tests cover 16, 24, 44.1, 48 and 96 kHz, callback boundaries and saturation. Empty recognition produces visible feedback; recognised words also appear instead of being silently ignored.

The owner subsequently confirmed the spoken map command worked. The installed native app visibly showed Map & journeys open and the reply Your map is ready. Open Plan a journey to choose where to go. Capture was then stopped and the final interface refreshed without relocking. This confirms that command path in the configured environment, not every device, accent, integration or arbitrary spoken question.

The local Vosk decoder separately recognised the synthetic test phrase through the production PCM conversion and authenticated endpoint. An explicit engine=local query forces offline decoding; it cannot fall through to the cloud. Invalid engine choices are rejected. The default configured provider is unchanged, and offline hardware acceptance remains unverified. A synthetic speaker-to-microphone test did not recognise words and was not counted as a pass; echo cancellation may suppress computer playback.

Apply jjrvis-capture-rate.patch after jjrvis-voice-phrase.patch against CAPTURE_RATE_BASES.json. Copy the new tests and restart the existing broker. No native rebuild, model download or new credential is needed. Runtime speech, screenshots and owner data are excluded from Git.

Validation: 28 targeted JavaScript tests passed; 22 voice-route tests passed. A synthetic phrase generated locally was resampled from 24 kHz and recognised as moneypenny show my map by the explicit local endpoint. Offline routing tests prove that enabled cloud configuration is not consulted for a local request. The successful live map test used the existing configured transcription selection.
