# Movement, visual briefing and natural-look update — 20 October 2026

Implemented in the owner's local Mac app and Studio. This is an incremental handover; it is not a standalone customer server.

## Visible changes

- Restored overview character dragging. Rotate person temporarily lifts the avatar above overlapping globe controls; Finish rotating restores world interaction.
- Move & view provides turn, walk, dance, stretch, framing, natural idle and Stop. The same supported movement phrases bypass the text model and reach the existing bounded motion controller. An origin/source checked request and acknowledgement report preparation failures, unsupported movements and timeouts. Actual controller-state events distinguish starting motion from queue acceptance.
- The current character revision is visible. Studio reset loads the current local candidate instead of silently reverting to the original sample, with a previous-look comparison.
- First-page headlines animate through supplied stories and publisher images unless dismissed. Only approved HTTPS publisher image hosts are accepted, with no-referrer and failed-image removal. Initial automatic progression stays within public news; it does not advance into private messages. Speech remains opt-in. A small presentation gesture is requested without overriding deliberate motion.
- Short audio gain ramps reduce discontinuities at phrase edges. Five recent source WAVs had no clipped samples; audible crackle is not certified resolved by this measurement.
- Explicit requests can launch known installed Mac apps through the existing owner-only fixed-app catalogue. This does not establish general app editing, unattended control or account access.

## Character candidate and size

The private v31 source replaces the heavy hair geometry with Ashley May hair by Elvaerwyn, from MakeHuman hair02 CC-BY. The source licence says CC-BY without a version. Geometry is transformed to fit; retain the attribution. Skin colour is Young Female Hairless by bobby_03 from the CC0 skins01 pack. Neither is represented as a photographic scan. Pack provenance:

- https://files.makehumancommunity.org/asset_packs/hair02/hair02_ccby.zip — SHA256 c681e5efd37df4007a52253a8d071aedbfe3b614f199d8dae4ae76d5bd7d95c9
- https://files.makehumancommunity.org/asset_packs/skins01/skins01_cc0.zip — SHA256 7495ab99287053bd19ff1636114e64b608994d9f7437fea6cc75ea387f96dba9

The latest v32 further reduces forward chest projection by at most 35 mm, relaxes angular fabric imprints after restoring split-vertex adjacency, and uses a plain fabric base colour. Existing face, speech shapes, skeleton and earlier files remain. The private model is approximately 27.2 MB; v31 reduced base triangles from 291,992 to 156,031, about 47%. These are asset measurements, not whole-app memory measurements. No private body mesh, portrait, account file or runtime binary is published. Legacy body redistribution rights remain unresolved.

## Installation

Apply `jjrvis-motion-recovery.patch` after `jjrvis-workspace-polish.patch` only when workspace.js matches MOTION_RECOVERY_BASES.json. Check/apply with `git apply --check --unidiff-zero` and `git apply --unidiff-zero`. Copy the updated scene-layout.js, command-scene.css and included test to their matching locations. The patch has been applied in a temporary copy and verified byte-for-byte against the live source.

Studio source and tests are in the repository. Private model builds require the owner's existing v30 source and locally installed credited asset packs; run refine_natural_v31.py, then refine_fit_v32.py with Blender. Both preserve existing outputs. Restart Studio and refresh JJRVIS. This update does not require disabling the private unlock or microphone controls.

## Acceptance and remaining roadmap

Native Mac UI checks showed the new revision, a completed front-to-back turn, direct drag to a side view, and a publisher-image news card. Automated Studio tests and geometry contracts cover the rig, speech shapes, gesture segment lengths, fixed character selection, comparison and phrase envelope. See MOTION_RECOVERY_VERIFICATION.json.

Photographic appearance remains unachieved: the character is still visibly CG. Realistic arbitrary motion also remains unachieved: supported skills and imported clips are bounded, with no general collision-aware physical planner. Finish a licensed high-quality face/hair/garment source and review neutral/profile/rear/voice/motion at actual app resolution before calling it photographic. Build authored locomotion/contact transitions before promising any requested body action.

Autonomy remains contextual idle motion, briefing presentation and supported direct commands. Expand application tools one verified workflow at a time, beginning with file search, selected-document questions, app launch and reversible drafts. Require completion evidence and visible cancellation. Messaging, trading, payments, deletion and access grants retain their separate authority. Do not market unlimited computer control, automatic private-account access or customer readiness.
