# Portrait and natural motion — 21 October 2026

The current local character has clearer eyes, cooler dark-blonde hair, softer frontal light and reduced procedural skin relief. Three hair cards had crossed the left outer eye; v38 sweeps those cards outward without moving their roots, changing UVs or altering the face. The measured eye-band intersections drop from 16 vertices to zero. The earlier floating-nail and blouse-cuff repairs remain in the asset.

The v37 preparation fits 760 brow-strand roots to the existing face with a maximum 0.201 mm root clearance and transfers five brow-expression targets. The complete body, face, clothing and speech-shape coordinates remain unchanged. Run `refine_portrait_v37.py` from private v36, then `clear_eye_fringe_v38.py` from v37; both preserve earlier sources and refuse overwriting their outputs.

The runtime uses the existing environment, direct light and fill light. It does not allocate another reflection map, post-processing pass or transmission capture. Hair and lash cards no longer cast coarse shadow silhouettes over the face. Lashes use alpha coverage instead of a blended card. The existing neutral skin texture remains; local alternatives add heavy baked makeup and provide no higher-resolution face scan.

Breathing uses a shorter inhale and longer exhale with continuous joins and slow tempo variation. Idle movement leaves the pelvis/feet planted. Presentation gestures are small, honor their requested intensity and alternate hands. Reused idle-rotation objects avoid per-frame quaternion allocation. Duplicate head-movement defaults were removed, and user movement settings retain a restrained scale.

## Evidence and limits

The actual v38 export passes the geometry, skeleton, corrective and speech-viseme contract. 65 Node tests and 66 Python tests pass, with two Python skips. Native visual results are recorded in PORTRAIT_MOTION_VERIFICATION.json. Texture/rig measurements do not prove photographic realism, arbitrary motion or full autonomous application control.

The underlying face remains a generic authored mesh with a 2K whole-body colour atlas and procedural detail maps. This increment does not turn it into a scanned human face or establish customer-release rights for the legacy body asset. It is a verified improvement to the current character. The private v38 runtime export, generated styling studies, screenshots and records remain outside the public source repository.

Publication clarification: the original parametric body was added as a named
root-level handover source on 21 October, and an older root anatomy study was
already tracked. The v38 runtime export and captured scan data remain local.
See `CHARACTER_SOURCE_PROVENANCE.json` at repository root for the exact exceptions.
