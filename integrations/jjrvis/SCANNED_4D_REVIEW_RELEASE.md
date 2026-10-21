# Captured human review — 21 October 2026

The local studio now has a separate **Realism previews** page at
http://127.0.0.1:8090/realism . It compares actual captured human detail with a
speaking-rig study, without replacing the working v38 conversational character.

## What works locally

- **Recorded 4D:** the complete Aliyah dance004 capture is converted to 556
  independent GLBs at 15 fps, about 37 seconds. Play, pause, scrubbing, orbit,
  full-body framing and a close-up of the current pose work in the browser.
- **Picture options:** Clearer detail uses matching 1024px images (508,759,956
  bytes across the sequence); Lighter playback uses 512px images (427,166,576
  bytes). Both retain the same captured poses. Original 2K source images remain
  local and unchanged. These are texture dimensions, not a claim of 4K facial
  detail or a whole-app memory measurement.
- **Bounded playback:** one decoder and at most three cached frames; two-frame
  lookahead. Hidden documents pause. Superseded decoding, mode switches and page
  disposal release image, texture, mesh and skeleton resources. The whole clip is
  not decoded into memory.
- **Scanned rig:** the private Claudia prototype has 88 bones, 54 canonical body
  and eye names, real jaw/blink/smile deformations, 14 approximate articulating
  visemes and neutral silence. The preview supports wave, mouth and blink studies.

The 4D source changes both mesh connectivity and UVs between frames, so it is
evaluated independently per frame. Blending positions across an assumed common
topology would corrupt the capture. The viewer keeps the last valid frame while
buffering rather than racing past every late decoder.

## Verification performed

- 83 JavaScript tests and 90 Python tests passed; two Python tests skipped.
  Syntax checks passed. Tests exercise actual player lifecycle behavior, slow
  decoding, cancellation, modes, errors, quality switching, camera framing and
  private-route boundaries.
- Both complete conversions were verified with 556 distinct exported geometry
  buffers and 556 distinct embedded images. Detail and light pose hashes match.
- The packaged scanned builder was run in a separate derived output directory.
  Original source checksums remained unchanged. Rebuilt position and morph
  buffers match the previously reviewed prototype; 88-bone transforms are finite
  during the wave test.
- Browser inspection confirmed rendering, playback/pause, the final timeline
  frame, camera rotation to the back, both quality choices and close-up framing.
  The browser captured no warning/error entries during this review. The owner
  proof image is in Downloads; it is not a public repository asset.

See `SCANNED_4D_REVIEW_VERIFICATION.json` for exact scope and asset hashes.

## Limits and distribution

This 4D clip is a recorded performance, not an autonomous person. It cannot
generate a new requested pose or spoken reply. The scanned jaw/blink recipes
are approximate: natural pronunciation, reliable teeth visibility and complete
facial controls have not passed live acceptance. Direct TalkingHead loading
requires missing-channel handling. The current CG assistant remains active.

The free samples come from [Renderpeople](https://renderpeople.com/free-3d-people/).
Its [terms](https://renderpeople.com/general-terms-and-conditions/) restrict
third-party app/SaaS use and extractable redistribution. These are private local
studies; no customer redistribution permission has been obtained. Original and
derived FBX, Blend, Alembic, texture and GLB assets stay outside Git. The new
review endpoints have not been added to the JJRVIS proxy or public deployment.

## Reproduction from authorised local sources

`scripts/character/convert_4d_review.py` accepts the directory containing the
official 2K Blender project, its Alembic cache and matching image sequence, plus a
separate new output directory. Use official Blender with `--disable-autoexec`,
two threads, `--step 2` and `--texture-size 1024` (or 512). It explicitly loads
each matching frame texture and writes the manifest atomically. `--resume`
accepts only matching existing derived frames. Embedded source scripts are not
executed, and no source scene is saved over.

`scripts/character/build_scanned_review.py` requires the pre-existing private
`Claudia-private-look-review.blend` and original download provenance. It does not
create that prerequisite or acquire vendor assets. It refuses existing outputs,
verifies original source hashes before and after, disables embedded scripts and
builds the source-specific review GLB into a separate directory. This script is
not a generic human or ARKit converter.

A fresh Git checkout has source and tests, not licensed captured models. Missing
local candidates return an explicit unavailable response rather than a simulated
success or a fabricated person.

The later 21 October handover also includes the original editable parametric body
at repository root. A separate older anatomy-study binary was already tracked.
Those files are distinct from the Renderpeople capture data described here; see
`GEMINI_HANDOFF.md` and `CHARACTER_SOURCE_PROVENANCE.json` at repository root for
the corrected file-by-file publication scope.
