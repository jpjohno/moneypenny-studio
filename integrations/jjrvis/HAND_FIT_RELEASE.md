# Hand attachments and cloth correction — 20 October 2026

Private style-v36 is selected automatically when present. The script repair_hands_fit_v36.py builds from the existing v33, preserves previous files and does not redistribute the private model.

## Fixes

The ten fingernail shells were 13.1–27.7 mm away from the actual hand surface in the source rest pose. Each shell is translated and fitted onto that existing surface with a 0.35 mm offset, then receives the nearest body surface's four strongest normalised skin influences. The build asserts a maximum rest-surface gap below 0.5 mm. This fixes the detached bright dots rather than hiding the whole hand.

The wave now aligns the fingers upward and the palm forward using actual hand/finger landmarks. It blends through the existing skill weight instead of rotating an arbitrary local wrist axis. The default arm pose bends the elbows slightly and brings the hands closer to the torso, with authored clavicles and segment lengths preserved. Head movement is reduced. A wave keeps the current camera framing so it no longer shrinks to an unnecessarily distant full-body view.

The blouse front uses a smoother connected fit. The final fit keeps sleeve/side boundaries and a portion of original depth relief; live review rejected an earlier full-strength flattening because it pulled the underarm fabric inward. The sleeve cuffs were incorrectly assigned the skirt material by a height-only split; 6,884 arm-weighted faces now use the blouse material. Body and facial shape coordinates remain unchanged. This is a garment/attachment correction, not a new photographic face or production cloth simulation.

## Verification

61 Studio Node tests and 66 Python tests passed, with two Python skips. The wave test checks upright fingers on either hand, unchanged finger segment lengths and an untouched opposite shoulder/hand. The actual private v36 GLB passed the geometry, skeleton, corrective and viseme contract. Native checks are recorded in HAND_FIT_VERIFICATION.json; source measurements are separate from visual acceptance.

Use the existing Studio deployment workflow, run the build script with Blender only when the private source is available, restart Studio and refresh JJRVIS. No broker permission or authentication change is required. Runtime character binaries, private records and screenshots remain local.
