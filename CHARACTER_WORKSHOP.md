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
