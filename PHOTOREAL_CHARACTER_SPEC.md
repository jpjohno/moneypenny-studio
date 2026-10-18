# Production adult character and wardrobe specification

Requested target: a fictional adult human who remains convincing at photographic close-up and in full-body movement. Current status: **not achieved by the bundled CC0 sample**. This file makes the missing asset work concrete; it is not an asset-completion claim.

## Required asset layers

- Complete adult body mesh underneath clothing, with continuous topology, realistic skin surface/normal/roughness maps and anatomically correct external detail. Required underlying features must actually exist in the source mesh/textures; a checkbox or a garment-coloured surface is not a substitute.
- Face with believable proportions, asymmetric detail, eyelids, tear line, eyes with correct corneal depth/refraction, teeth, tongue and natural lip closures.
- Realistic hair, eyebrows and eyelashes using suitable groom or high-quality cards. Check the profile and rear of the head, not only a frontal portrait.
- Separate fitted underwear/coverage layers, outer garments and footwear. The requested starting catalogue is office, casual and evening dress, with flats, trainers and a properly modelled raised-heel option.
- Actual clothing and shoe geometry with compatible skin weights and corrective shapes; a material-colour change does not fulfil the wardrobe requirement.

## Rig and motion

- Full humanoid skeleton, fingers and facial shapes, plus explicit joint limits and body-contact/grounding constraints.
- Mouth shapes aligned to the chosen speech system, blinking, gaze, brows, cheeks and emotion blends that do not break lip closures.
- Authored locomotion and transitions: idle, weight shift, turn, walk, sit/get up, kneel/get up, lie on back/get up, stretch, bow, dance/jig and splits/recovery.
- Inverse kinematics for reaching shoulders, face, torso, hips and knees, with palm/finger orientation and collision/contact review.
- Dressing and undressing clips matched to the garments, with coverage maintained as specified. A runtime mesh swap is only a prototype transition, not a realistic removal simulation.
- Autonomy chooses a motion plan based on persona, context and activity level. Plans may compose skills and authored joint timelines; arbitrary software execution is excluded.

## Delivery package

- Source scene and rig, textures with licences, a documented wardrobe slot map, animation clips, facial mapping and an asset manifest.
- Browser target: self-contained GLB with supported humanoid bone names, Oculus mouth shapes and appropriate PBR textures; optional higher-quality engine source for rendering comparison.
- Character metadata must distinguish adult identity, complete anatomy, coverage layers, tested wardrobe combinations, facial compatibility, body-motion capabilities and commercial rights. Do not set those fields true without asset inspection.

## Current implementation versus target

| Area | Current studio | Missing production work |
| --- | --- | --- |
| Person | Existing CC0 MPFB character | Original photographic-quality face/body/hair/eyes |
| Underlying anatomy | Not certified or completed | Complete adult anatomical source asset and explicit inspection |
| Clothing | Separate procedural skirt, dress-skirt and waistcoat layers over the original coverage outfit | Artist-fitted outfits, true underlayers and collision/corrective work |
| Footwear | Simple skinned prototype shoe surfaces | Proper shoe lasts, soles, heels, fit and foot-pose corrections |
| Movement | Procedural full-body skills, reach IK, autonomous planning and bounded custom joint timelines | Production motion clips, joint/contact/collision constraints and transition polish |
| Dressing | Outer-layer selection and a gesture/turn sequence | Actual garment removal/putting-on animation and cloth handling |
| Rendering | Local PBR, adjusted exposure/light and contact shadows | Final asset-dependent skin/eye/hair shading and visual acceptance |

## Free tool routes checked

[Blender/MPFB](https://static.makehumancommunity.org/mpfb.html) provides a free authoring route, and MakeHuman's [asset packs](https://static.makehumancommunity.org/assets/assetpacks.html) list licences for individual garments. Free software does not itself produce a finished custom person or transfer rights to every downloaded asset.

[MetaHuman](https://www.metahuman.com/license) is a candidate high-quality character pipeline under Epic's applicable licence conditions. It needs actual character creation/export and rig/wardrobe integration. No MetaHuman account, agreement, install or character import was completed in this run.

The existing avatar remains clearly labelled as a sample until a production asset passes the visual and motion checks. No naked generated photograph, private portrait, borrowed likeness or non-commercial sample has been substituted and represented as the finished commercial character.
