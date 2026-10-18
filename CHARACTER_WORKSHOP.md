# Character and motion workshop

Implemented on 18 October 2026. This is the source-editing and animation pipeline; the photographic adult character and realistic dressing asset remain unfinished.

## Latest dressed performance candidate

Double-click **Open Performance Character.command** to open the local `Moneypenny-Performance-Final-Fit-v3.blend`. This preserves the anatomy study and every earlier iteration. **Build Performance Character.command** reproduces the successive build stages after the anatomy source exists; builders preserve existing scenes rather than overwrite artist edits.

The new dressed source adds 15 Oculus speech shapes and 52 ARKit facial shapes, separate gaze-weighted eyes and corneal caps, transferred teeth/tongue/lash deformations, and a 54-bone skeleton. It has an actual CC0 2048px skin colour texture, procedural pores/roughness and subsurface shading. The export bakes the procedural surface to actual 2048px normal/roughness maps. These are not photogrammetry or scanned PBR textures. The restored ponytail is supplemented by 3,248 individually modelled and skinned strands; this is an original procedural groom, not scanned hair.

The office blouse/skirt and ankle shoes are separate fitted, skinned source meshes with wardrobe-slot extras. Fit iterations repaired bust penetration and toe exposure. Four small authored elbow/knee volume shapes are driven by measured joint bend in Blender and by `static/correctives.js` in the studio. They are modest volume corrections, not a complete sculpted pose-space, muscle, collision or cloth system. Neutral outfit, moderate arm pose, hands, bare feet, shoe coverage, portrait, mouth opening and blink renders are available under local ignored `verification/`.

The private self-contained `Moneypenny-Performance-Candidate-v6.glb` is 40,309,488 bytes, under the studio's 80 MiB limit. `node scripts/character/verify_performance_glb.mjs` loads its actual skeleton, skinning and morph geometry with Three.js and checks real mouth/blink displacement and corrective bindings. Image definitions are removed only in that geometry test: it does **not** certify browser texture decoding, real-time speech playback, visual acceptance or character import. No earlier declined character upload has been retried or bypassed. The speaking website still uses the clothed sample.

Reproducible stages are `build_performance_character.py`, `polish_performance_fit.py`, `detail_performance_character.py`, `finish_performance_fit.py` and `prepare_performance_export.py`. `review_performance_details.py` renders the saved final-fit scene independently. Reports remain in `.runtime/character-workshop/`. The current result is visibly computer-generated. Photographic realism, unrestricted natural movement, clothing fit during extreme poses, dressing simulation and soft-tissue dynamics remain unfinished. Native render/morph checks are separate from live audio-to-face acceptance.

`finish-assets.json` pins skin, hair and facial-data downloads with hashes, sizes, licences and official catalogue links. The selected skin is MargaretToigo's CC0 natural-makeup skin. The exploratory Elvaerwyn Lara hair is CC-BY and hidden in the final source; its attribution remains. The anatomy patch's unresolved licence notice still prevents claiming commercial redistribution clearance. No generated model, texture, render or source asset is pushed to the public repository.

## What is installed on this Mac

- Blender 4.5.14 LTS, Apple Silicon, in `~/Applications/Blender-4.5-LTS.app`.
- MPFB 2.0.18, installed and enabled from Blender's official extension service.
- Editable source scene: `.runtime/character-workshop/Moneypenny-Character-Workshop.blend` (local, excluded from public Git).
- Double-click **Open Character Workshop.command** to open that scene.

The scene contains the existing clothed CC0 sample, a lighting/ground setup, limb IK targets and a separate hidden collection with a newly generated adult female MPFB base and Mixamo rig. IK constraint influence starts at zero to preserve the sample; enable it while authoring a pose. The new body is an editable base, not a certified anatomically complete or photo-real asset. Surface anatomy, detailed skin/hair/eyes, facial shapes, garment fitting and corrective deformation need further source work and inspection. The adult source is hidden so it cannot be mistaken for the completed on-stage person.

The builder is `scripts/character/build_workshop.py`. It preserves an existing workshop file rather than overwriting edits. To build in a fresh checkout after installing the tools and studio sample:

```sh
~/Applications/Blender-4.5-LTS.app/Contents/MacOS/Blender --background --python scripts/character/build_workshop.py -- "$PWD"
```

Downloads were verified against official SHA-256 values; exact versions/URLs are in `character-tools-manifest.json`. No gatekeeper settings, system security controls or application agreements were changed.

## Separate body editor

### Adult anatomy study — 18 October, later update

**Open Body Editor.command** now prefers the actual local `Moneypenny-Adult-Anatomy-Study-v3.blend`. It is open in Blender and contains a continuous adult body surface with 13,848 vertices, 13,828 faces and the existing 52-bone skeleton. The original body source and earlier studies are preserved.

The study adds a fitted, welded 168-face external vulval patch, genuine MPFB nipple/umbilical detail targets, a shallow closed perianal contour, 478 individually modelled and skinned body-hair strands, and fitted eyes, teeth, tongue, eyebrows, eyelashes, ponytail, short fingernails and toenails. Its five editable shape keys are **Breast volume**, **Nipple projection**, **Nipple diameter**, **Gluteal volume** and **Perianal surface detail**. These are Blender authoring controls; no live website body editor is implied. The perianal contour is external surface modelling, with no internal canal or medical accuracy certification.

`scripts/character/refine_body.py` builds this separate study, refuses to overwrite it and retains the source profile and asset notices in the scene. `Build Adult Anatomy.command` prepares the pinned assets and opens the study. No legacy MHX addon is installed or executed: the builder reads its inert topology/fitting data. `scripts/character/inspect_anatomy.py` independently checks the saved mesh and generates neutral front/rear/side renders under ignored `verification/`.

Actual checks passed: zero nonmanifold edges across the whole body and the anatomical join, zero unweighted body vertices, finite output at all five control extremes, and finite moderate arm/leg deformation with 0.371 m maximum movement. Neutral front/rear/side renders and the actual Blender viewport were inspected. These are structural and moderate-pose checks, not certification of every extreme pose, soft tissue, cloth collision or photographic quality. Fitted parts and body hair follow skeleton weights; changing the underlying macro body dimensions requires a refit/rebuild.

The official system and nail packs are catalogued as CC0. The legacy external-anatomy data embeds an **AGPL3** notice, while its author's [licence clarification](https://thomasmakehuman.wordpress.com/license-information/) describes extra importer content as CC0. Both notices and exact hashes are retained in `scripts/character/body-assets.json` and the local scene. **Commercial redistribution is not cleared** until that conflict is resolved. Generated meshes, source asset downloads, textures and renders remain local and excluded from public Git. This study is not installed as the speaking website character; facial visemes, photographic skin/hair work, fitted wardrobe and production corrective deformation remain unfinished.

The earlier `.runtime/character-workshop/Moneypenny-Adult-Body-Source.blend` remains available as the parametric source, and the launcher falls back to it if the anatomy study has not been built. This scene contains the MPFB adult base surface and a 52-bone Mixamo rig, with the clothed sample hidden as reference. It preserves the original performance workshop. Its source has smooth shading, editable subdivision, preserve-volume deformation and an initial skin material using the existing CC0 diffuse image, subtle procedural bump and subsurface shading. Those procedural nodes require baking before browser export.

The MPFB human controls support height, weight, muscle, proportions, breast size and firmness. The builder accepts `scripts/character/body-profile.example.json` (values 0–1), applies shape before fitting the rig and preserves an existing body scene. This is source authoring, not live browser body morphing. Clothes need refitting after shape changes.

The earlier base's source report still records its original unfinished state. The later study supplies the anatomical geometry and fitted parts described above; photographic hair/skin, makeup choices, facial speech shapes and extreme-pose corrections remain unfinished. The live character remains the working clothed sample, with improved skin/eye materials and three adjustable lighting looks.

The genuine NVIDIA motion setup and native Mac tests are described in `NVIDIA_MOTION.md`. A motion generator does not manufacture the body or clothing asset.

## Use the motion library

1. Open **Motion library** in the studio. Play, pause/resume, scrub to a chosen time, loop and adjust speed or transition time. The three included studies are bow and shoulder-stretch timelines plus an IK wave actually baked/exported from Blender to GLB. These are authored studies, not motion capture or finished production human animation.
2. Add a self-contained **GLB**, **BVH** motion-capture file or **.motion.json** timeline under 24 MB. Assets are stored in `.runtime/motion-library`, on this Mac only. GLB files may contain multiple clips. Only animations are applied; their model meshes/textures are not added to the person.
3. Common Mixamo and CMU/BVH bone names map automatically. Use **Animation bone mapping** for other skeletons. Retargeting uses Three.js's skeleton utilities on a clone, preserving the live person during preparation. Imported motion is sampled at 30 fps, limited to the first 60 seconds and kept in place horizontally.
4. Save comma-separated **Words that request this movement**. Those words can select the loaded clip in the conversation or direct-movement field. This expands the command vocabulary without writing a new hard-coded pose. Include a reviewed clip in independent movement to let the persona choose it; those autonomous clips yield to a new conversation turn.
5. Review foot contact, pelvis motion, knees, shoulders, fingers, clothing and transitions on the actual character before treating a clip as production-ready. Arbitrary imported rigs and extreme poses are not automatically certified.

## Rig controls

**Show skeleton and drag handles** reveals the skeleton and a translation gizmo for the selected hand, foot or hips. Move the sliders or drag the handle to hold a target. **Plant both feet** holds foot targets while hips/hands move. Release a target or reset all controls when finished.

The body resets to a stable reference before each frame, avoiding feedback from the avatar's automatic hip-balance pass. Two-bone IK preserves limb lengths, uses a consistent bend plane and clamps unreachable targets. Output interpolation is time-based. These controls improve the motion foundation; they are not a complete muscle, contact or cloth simulation.

**Bend over** now selects a clothed forward-hinge study directly from chat, with planted feet, lowered hand targets and eased upright recovery. **Turn around and bend over** retains the turn's heading during the bend and afterwards; another directed turn faces back again. Direct action plans take priority over model-generated conversational gestures. Pure supported commands run locally and acknowledge the queued movement without asking the chat model to agree. A geometric pose remains separate from production motion capture, garment collision and photographic acceptance.

The GitHub source includes all build stages and `LOCAL_CHARACTER_ASSETS.json`, an inventory of seven saved local deliverables with sizes and hashes. Actual character binaries, source packs, model weights, private runtime state and renders remain excluded. Refresh the inventory with `python scripts/character/inventory_local_assets.py` after saving artist refinements; unsaved Blender changes are not captured. The open anatomy-study scene's unsaved edits were preserved.

Splits now use leg IK and planted feet rather than raw local thigh rotations. Kneeling/seated poses use grounded targets. The lying study rotates around the pelvis rather than the feet. **Foot on seat** adds a clothed supported-step study with either foot, a closed opaque seat, a planted standing foot, a pelvis shift and eased lift/lower. Stop releases it and lets the rig settle back to rest. Text such as “Put your left foot on the toilet seat” selects the same study. It is excluded from the default autonomous pool and does not infer intimate hygiene actions. These are kinematic pose studies, not physics balance, collision-certified contact or finished motion-captured sequences.

## Garments and dressing

In **Outfit changes with movement**, choose a garment, time and visibility state, then add a change to the selected clip. Changes follow actual animation playback time and pause with the movement. They persist in this browser. A matching authored dressing clip and well-fitted garment are still required for a realistic result; visibility timing alone is not cloth handling.

Production GLBs can expose separate garment nodes using Blender custom properties `wardrobeSlot` (for example `top`, `bottom`, `shoes`) and optional `wardrobeLabel`. Export extras with the GLB. The original sample's fixed coverage outfit remains underneath the prototype layers; no completed underlying anatomical model is implied. Detailed adult external anatomy, underlayers, garment fitting and natural undressing/putting-on animations remain in `PHOTOREAL_CHARACTER_SPEC.md`.

## Personas and the local model

**Saved personas** reads the model catalogue from the existing local Open WebUI container in SQLite read-only mode. It reads model presets only, not users, credentials, chats or auth tables. It never modifies WebUI's database. The installed WebUI is 0.11.4; its two saved presets currently use `uncensored-3b`, with no attached knowledge collections.

Create/save named personas in the studio, load an existing WebUI persona or export a compatible model JSON for WebUI. Studio saves are local copies. Saved WebUI system instructions are used as stored. A persona with attached knowledge is explicitly refused by this direct-Ollama bridge until an authenticated WebUI chat adapter is configured; knowledge must never be silently dropped and represented as used.

The answer model defaults to installed `uncensored-3b:latest`; its actual name is shown below the stage. “Uncensored” identifies the model package, not a guarantee of any response or unlimited physical capability. Voice identity remains separate.

## Professional asset routes checked

- [Blender 4.5 LTS](https://www.blender.org/releases/4-5/) and [MPFB](https://extensions.blender.org/add-ons/mpfb/) are the installed free authoring route. [MPFB rigging documentation](https://static.makehumancommunity.org/mpfb/docs/characters/rig.html) describes compatible rigs and IK helpers.
- [Adobe Mixamo](https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html) supplies humanoid animation and auto-rigging, free with an Adobe ID under Adobe's applicable terms. No Adobe account/session, acceptance or animation download was completed here.
- [CMU motion capture](https://mocap.cs.cmu.edu/) is an additional source. Its stated terms allow inclusion in commercial products but prohibit direct resale of the data. No bulk crawl or unreviewed asset bundle is included.
- [MetaHuman hardware requirements](https://dev.epicgames.com/documentation/metahuman/metahuman-hardware-requirements-in-unreal-engine) list substantially higher recommended hardware and note that M1 Macs cannot render hair strands. This Mac is an M1 with 16 GB, so MetaHuman is not represented as an installed, proven photo-real route here.

No professional application makes every conceivable movement automatic or guarantees anatomy/skin/cloth quality by installation alone. The library, rig and workshop now support building and integrating that work without pretending the sample is finished.


## Blender to web studio motion workflow

The complete project now separates the Flask server (`app.py`) from Blender tools (`scripts/character/studio_controls.py`). The Desktop/main Blender script remains available in Git history at `e85c2f7`; it is not the web server. Its unbound anatomical sliders and intimate actions were not integrated. Existing user Desktop scripts and unsaved Blender edits were not run or overwritten.

1. Open `Moneypenny.code-workspace` in VS Code. The task **Moneypenny: open web studio** runs the web app. Continue can keep using the already installed Ollama model `cognitivecomputations/dolphin-llama3:latest` at `http://127.0.0.1:11434`; its global configuration is unchanged. Conversation controls and motion remain separate from code editing.
2. Run **Open Studio Rig Controls.command**, or the workspace task **Moneypenny: open Blender motion panel**. It resolves `~/Applications/Blender-4.5-LTS.app/Contents/MacOS/Blender` on this Mac. Set `MONEYPENNY_BLENDER` for another executable. The default source is the existing local dressed `Moneypenny-Performance-Final-Fit-v3.blend`. To use a different saved scene: `python3 scripts/launch_blender.py --file /absolute/path/source.blend`. This opens a separate Blender instance and does not save or replace a currently open scene.
3. Select the intended rig (or a mesh with an armature modifier). Open the 3D viewport sidebar with **N**, then **Moneypenny**. **Remember current pose** stores the pose on that rig. Edit another pose; **Animate to remembered pose** creates a new action from the current frame, with quaternion interpolation over the chosen transition frames. The previous action is retained with a fake user. This changes the active action/rotation representation intentionally and supports Blender Undo. It does not zero every rig in the scene. Rigs with bone constraints or active NLA tracks are refused for this simple transition tool; animate their own controllers normally instead.
4. Set the scene start/end range to the clip, at most 60 seconds and 1,800 frames. In Object Mode choose **Export movement for web studio**. Export evaluates Blender's scene animation/constraints. The GLB contains the selected skeleton, animation and a three-vertex skin carrier, with no character meshes, textures or clothing. Selection, active object and current frame are restored; temporary objects are removed even on error. The source .blend is not saved automatically.
5. In the running web studio, use **Motion library → Add animation**, select the exported GLB and review its retargeted playback on the existing clothed sample. Add words to request the clip or opt it into independent movement. Unknown bone conventions need **Animation bone mapping**; export is not a guarantee that arbitrary skeletons match. Facial morphs and cloth are not included in this motion-only route. New character upload acceptance remains unverified; this integration does not retry it.

Verification on 18 October: Blender 4.5.14 created a real 24-frame pose transition on a disposable four-bone rig, preserved a second rig and the previous action, rejected constrained pose rewriting, exported GLB and restored scene state. The same GLB loaded through Three.js and the studio retargeter, producing finite tracks and actual spine movement on the live sample's skeleton. These checks do not prove production mocap quality, arbitrary motion, clothing fit, photorealism or acceptance on another computer.

Repeat from the repository root:

```sh
python3 scripts/launch_blender.py --check
"$HOME/Applications/Blender-4.5-LTS.app/Contents/MacOS/Blender" --background --factory-startup --python-exit-code 1 --python scripts/character/verify_studio_controls.py -- .runtime/studio-controls-test.glb
node scripts/character/verify_motion_export.mjs .runtime/studio-controls-test.glb
```


## Surface review continuation, 18 October 2026

The working v6 source is preserved. Three additional packed Blender sources and browser candidates were built locally:

- v7: spatial face/body roughness, multiscale baked micro-normal maps, revised corneal/iris response, short tapered eyebrow filaments and portrait lighting. The skin colour is still the existing MargaretToigo CC0 2048px painted atlas, not a scan.
- v8: a replacement 12,000-strand cap-following ribbon groom covering the front scalp, 42 expression shapes transferred to the brow filaments, and restrained iris reflections.
- v9: scalp-cap fitting (1,941 moved vertices) with preserved UVs, weights and relative shape displacements. Its self-contained GLB is 51,148,284 bytes and retains 54 bones, 15 speech visemes, four corrective bindings and fitted clothing. Native portrait and full-body renders are in `verification/surface-v9-portrait.png` and `verification/surface-v9-full-body.png`.

Actual source scripts, in order:

```sh
BLENDER="$HOME/Applications/Blender-4.5-LTS.app/Contents/MacOS/Blender"
"$BLENDER" -b -t 6 --python scripts/character/refine_surface_look.py -- "$PWD"
"$BLENDER" -b -t 6 --python scripts/character/rebuild_surface_groom.py -- "$PWD"
"$BLENDER" -b -t 6 --python scripts/character/conform_surface_cap.py -- "$PWD"
```

They preserve existing versioned outputs; each requires its preceding local source. No source asset is fetched or silently purchased by these scripts. `Open Performance Character.command` and the Python Blender launcher prefer the new source when it exists. That stage preferred v9; the current styling revision below takes priority when present.

The deterministic native sweep uses 1,000 configurations: four hair arrangements, five skin-roughness scales, five subsurface amounts, five exposures and two fill ratios. Previews are intentionally only 128×160 at four samples; they are look-development comparisons, not 1,000 full-quality improvements. It writes per-image settings to ignored `.runtime/character-workshop/surface-sweep/renders.jsonl` and resumes without rerendering existing previews. Selected `--frame` configurations can be rendered at higher resolution and saved as separate review sources.

```sh
"$BLENDER" -b -t 6 --python scripts/character/render_surface_variants.py -- "$PWD" --count 1000 --size 128 --samples 4
"$BLENDER" -b -t 6 --python scripts/character/render_surface_variants.py -- "$PWD" --frame 368 --size 600 --samples 32 --save-source
node scripts/character/verify_performance_glb.mjs .runtime/character-workshop/Moneypenny-Performance-Candidate-v9.glb
```

**Visual assessment: photographic quality is not achieved.** The reviewed face, hair silhouette and materials still read as CG. v9 is an iterative surface study, not a completed photographic replacement. More render samples cannot supply absent captured skin detail or a production groom. The inherited anatomical-source redistribution question also remains unresolved; new generated models and textures remain local.

The user explicitly chose to keep the workflow free. Paid character tools were evaluated but not purchased or activated. The subsequent free route below supersedes those suggestions.


## Free CC0 source replacement study, 18 October 2026

The user chose **free assets only**. The selected research route is the [Vitruvian/CharMorph data assembled in VitruvianGodot](https://github.com/ibrews/VitruvianGodot), pinned at `bdecdcd537b4031fdd0fb299b7e4f93f084fffa0`. Upstream `NOTICE.md` identifies the character/maps as CC0 and its code/shaders as MIT. `scripts/character/free-surface-assets.json` pins 18 data/notice files and SHA-256 hashes (116,340,527 bytes total). Upstream executable scripts are neither installed nor executed. Godot-specific shaders and hair physics have not been represented as automatically portable. No payment, email subscription or vendor account is involved.

The free assembly uses a new fictional face and clothed body; it is not a restoration of the earlier detailed anatomical study. The upstream body export omits some skin hidden under clothing. The old complete body source and its controls remain preserved.

Free build chain, preserving each prior source:

```sh
python3 scripts/character/setup_free_surface_assets.py
BLENDER="$HOME/Applications/Blender-4.5-LTS.app/Contents/MacOS/Blender"
"$BLENDER" -b -t 6 --disable-autoexec --python-exit-code 1 --python scripts/character/build_free_surface_character.py -- "$PWD"
"$BLENDER" -b -t 6 --disable-autoexec --python-exit-code 1 --python scripts/character/optimise_free_surface.py -- "$PWD"
"$BLENDER" -b -t 6 --disable-autoexec --python-exit-code 1 --python scripts/character/refine_free_surface_face.py -- "$PWD"
"$BLENDER" -b -t 6 --disable-autoexec --python-exit-code 1 --python scripts/character/weld_free_surface_neck.py -- "$PWD"
node scripts/character/verify_performance_glb.mjs .runtime/character-workshop/Moneypenny-Free-Surface-v16.glb --free-surface
```

The unoptimised v10 source/candidate is preserved. Two oversize experimental exports (v11 and v12) failed the 80 MiB budget and were not promoted. The v13 browser copy loads the original packed images before resizing; it retains 2048px face colour/normal data, reduces selected body/hair/roughness maps to 1024px, uses JPEG colour encoding and simplifies hair geometry. v14 adds expression-linked brow/lash filaments and optical-eye geometry; v15 restores continuous neck skin and hides only the overlapping head-neck polygons. Native portrait/full-body review PNGs are in `verification/free-surface-v15-*.png`.

The new source has a 54-bone humanoid/gaze rig and a mouth/eye FACS bridge exposing 15 runtime viseme slots. Some phoneme slots reuse an authored source deformation, so this is not a claim of 15 independently captured mouth shapes. Authored elbow/knee corrective shapes and Godot spring-hair physics are absent from this new source. Extreme poses, all speech phonemes and photographic quality remain unverified. The runtime can fall back through the v9 study, v6 performance candidate and CC0 bundled sample.

**The 1,000-preview sweep actually completed:** 1,000 unique 128×160 four-sample renders, in 597.1 seconds. `verification/surface-sweep-index.html` browses the full local set and lists settings. These compare the v7 source; they are separate from the subsequent new CC0 character assembly. They do not establish photographic quality.


## Current clothed styling revision v24

The free full-character experiments were visually rejected. v14/v15 had neck seam problems; v16 welded 4,222 duplicate boundary vertices and passed the geometry checks, but still looked CG in the isolated browser review. None is the normal app default. Only the CC0 bob is reused in the current MPFB-based clothed character, fitted to its Head bone. No user photograph is bundled, uploaded or used as a texture.

`style_character.py` derives v24 from the preserved v9 source. It narrows the frame by 6%, adds a substantially fuller bust with shared body/garment deformation, makes subtle jaw/lip changes, brightens the iris to blue-green, and replaces the striped clothing with matte champagne/ink tailoring and an embedded weave normal. The CC0 bob is lengthened, given slight wave and a lighter varied blonde atlas. These are authored changes, not a photographic scan or measured bra cup size.

The complete Blender source is saved before an under-garment face mask is applied to the clothed browser export. This prevents covered skin showing through the blouse; hiding that garment is not a complete undressed-body view. v17/v18 were rejected for visible clothing breakthrough; v19 fixed coverage but its bob was too dark/short. All previous sources remain local.

The player now captures the imported bind pose before TalkingHead replaces it with generic shoulder rotations. It lowers arms by length-preserving IK while retaining the clavicles, and resets the body to this neutral before studio movements. Imported user characters retain the existing loading behavior. Slow continuous chest breathing and slight body sway are layered on the local studio character. This is kinematic animation, not muscle/cloth simulation.

```sh
"$HOME/Applications/Blender-4.5-LTS.app/Contents/MacOS/Blender" -b --python-exit-code 1 --python scripts/character/style_character.py -- "$PWD"
node scripts/character/verify_performance_glb.mjs .runtime/character-workshop/Moneypenny-Style-v24.glb
```

The build needs the existing local v9 and free v16 sources. Binary sources, render variants, private media and generated exports remain ignored/local; the repository holds the scripts, pinned free-data manifest and continuation instructions. Photographic realism, broad extreme-pose fit and natural speech/motion acceptance remain unfinished.

The final v22 styling pass removes solid eyebrow cards while keeping expression-linked brow filaments, uses cooler blonde hair and stronger blue irises, broadens the clothed bust deformation to avoid a narrow projected tip, and slightly defines jaw/lip forms. The local source and export are versioned separately from rejected v17–v21 experiments.

The user then preferred warmer, longer blonde hair and accepted the bust size. v23 keeps that bust, subtly slims the cheeks, uses the existing natural MakeHuman blue-eye atlas, and corrects 4,672 chest weights on body/blouse. Native hair is still card-based and has no collision physics; shoulder-length hair and clothing need broad motion review.

v24 adds root coverage under the bob and exports it with alpha MASK rather than BLEND to prevent card self-sorting gaps. The default local wave uses IK on one hand and retains the authored clavicles. Library clips remain available but are not certified for the enlarged outfit. Photographic quality has not been achieved.
