# Warmer character and translucent briefing — 20 October 2026

This local update builds on the movement recovery increment. Preserve the private package and configuration. Copy scene-layout.js, command-scene.css and presence_proxy.py plus the included tests only after comparing WARM_GLASS_BASES.json. Studio source comes from this repository. Restart the broker after its fixed asset allowlist changes, restart Studio after default character selection changes, then refresh the client. No Apple unlock, microphone permission or owner authentication is disabled.

## What changed

- Private style-v33 refits only the clothed front drape into broad connected oval volumes with the centre placket, side and neckline boundaries retained. Body, facial and speech shape coordinates remain unchanged. Earlier v32 is preserved. The new export is approximately 27.2 MB; no body/model binary is published.
- The local production character's default expression becomes a slight smile, with softer cheek/eye response, less downward head movement and small gaze changes. Existing speech visemes, blinks and explicit serious/thoughtful expressions retain ownership. Imported characters keep their own default expression. The mood copy preserves TalkingHead's gaze callbacks; structuredClone cannot copy these functions and caused a fallback during live review, which was corrected before publication.
- Idle posture uses small asynchronous torso and arm movements, with a smooth transition toward quiet. The hips no longer translate sideways during breathing. Ordinary autonomous gestures are smaller and avoid repeating larger gestures back-to-back. These are local bounded animations, not general physical planning. Hidden-stage pauses and existing frame/pixel budgets remain.
- Briefing panels are translucent, so the Earth stays visible behind them. Entrance, card exit/arrival and panel dismissal use bounded opacity/transform animations. No continuous blur pass, new render engine or background model call is introduced. The headline appears before the image to remain readable in smaller panels.
- A news-only automatic briefing leaves the stage when its last item finishes. Deliberate multi-topic briefings retain the end summary. Manual pause, close, reduced-motion and display-motion preferences are respected. Reopening during a closing animation cancels the stale dismissal rather than hiding the new panel.

## Validation and limits

Studio: 60 Node tests and 66 Python tests passed, with two Python skips. These include real gaze callbacks, preservation of explicit moods and mouth ownership, constrained autonomous selection, and existing rig/voice/render-budget checks. The actual v33 private GLB passed the geometry, skeleton, facial-shape and viseme contract. The garment source reports 3,974 refitted vertices and preserved body/face/speech shape coordinates.

Workspace: 15 isolated UI/card tests and 36 proxy tests passed. UI fixtures exercised close/reopen cancellation, reduced-motion dismissal, layout, card advancement and source boundaries. The new expression module is specifically owner-protected and fixed-host, with no credential forwarding or arbitrary module paths. Native review showed the new v33 ready marker and translucent illustrated briefing; final visible-render acceptance is recorded separately in WARM_GLASS_VERIFICATION.json.

The character remains CG. A softer expression and rounder clothed outline are not photographic completion or evidence of arbitrary movement. No new full spoken test, whole-app memory benchmark or customer-readiness certification was performed. Private source licensing caveats from the previous release remain.
