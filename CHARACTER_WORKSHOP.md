# Character and motion workshop

Implemented on 18 October 2026. This is the source-editing and animation pipeline; the photographic adult character and realistic dressing asset remain unfinished.

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

**Open Body Editor.command** opens `.runtime/character-workshop/Moneypenny-Adult-Body-Source.blend`. This second scene contains the MPFB adult base surface and a 52-bone Mixamo rig, with the clothed sample hidden as reference. It preserves the original performance workshop. Its source has smooth shading, editable subdivision, preserve-volume deformation and an initial skin material using the existing CC0 diffuse image, subtle procedural bump and subsurface shading. Those procedural nodes require baking before browser export.

The MPFB human controls support height, weight, muscle, proportions, breast size and firmness. The builder accepts `scripts/character/body-profile.example.json` (values 0–1), applies shape before fitting the rig and preserves an existing body scene. This is source authoring, not live browser body morphing. Clothes need refitting after shape changes.

Detailed external anatomy, realistic hair/eyes/nails, makeup choices, facial speech shapes and extreme-pose corrections remain unfinished. The source report explicitly marks anatomical detail and browser facial readiness unverified. No “remove clothes” operation has been represented as completing those features. The live character remains the working clothed sample, with improved skin/eye materials and three adjustable lighting looks.

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

Splits now use leg IK and planted feet rather than raw local thigh rotations. Kneeling/seated poses use grounded targets. The lying study rotates around the pelvis rather than the feet. These are pose studies, not a finished motion-captured lowering/recovery sequence.

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
