# Moneypenny: standalone persona platform

Proposed product plan, 18 October 2026. This is a development and validation plan, not evidence of sales, demand, partnerships or a finished photoreal product.

## Product

A visible, customisable adult digital person who can hold a hands-free conversation, stop when interrupted, remember the current discussion, choose appropriate movement, change outfits and follow up at agreed times. The customer chooses personality, appearance, voice and permitted capabilities independently.

Moneypenny is a standalone application and runtime. Jarvis can later become one optional capability provider. The avatar, wardrobe, conversation and movement must continue working without Jarvis, and connecting Jarvis must not grant every persona unrestricted access to mail, files or other systems.

## First customer and first product

Start with a private desktop assistant for an individual professional: conversation, planning, rehearsal, useful questions and agreed check-ins. A second test group can use fictional companion personas. Keep those profiles separate so a business persona behaves appropriately during work.

The first product should have one excellent original character and three properly authored outfits. A large catalogue of mediocre characters would distract from the central test: does this feel like an attentive person rather than a talking menu?

The current local studio is an engineering prototype. It has the conversation, motion and wardrobe foundations, but the sample character and procedural garments do not meet a photographic visual acceptance bar.

## Four separable systems

1. **Identity and assets:** body, face, skin, eyes, hair, fitted garments, shoes, voice identity and verified usage rights. A character package declares its rig, facial shapes, wardrobe slots and supported animations.
2. **Conversation:** microphone, speech detection, transcription, turn ownership, interruption, language model, streaming speech and timed follow-ups. A personality is editable data, not code execution.
3. **Embodiment:** locomotion, poses, gestures, hand targets, gaze, expression, autonomous behaviour, imported motion clips and authored joint timelines. The planner proposes motion; the renderer executes validated data.
4. **Capabilities:** optional adapters for tasks, calendars, document search and reviewed draft preparation. Consequential actions retain explicit review and a factual completion result.

This split allows the same person to be used in an office, a personal companion or a Jarvis panel without changing the voice or rebuilding the character.

## Visual production decision

Two implementation paths should be compared with the same original character brief:

| Path | Value | Trade-off |
| --- | --- | --- |
| Browser-native GLB/PBR | Convenient local app, direct interaction, broad distribution, editable integration | Needs an expertly authored real-time asset; this sample is insufficient. Hair, skin shading, cloth and body contact require more work. |
| High-quality real-time engine, such as Unreal/MetaHuman | More mature skin, eyes, hair, control rigs and clothing workflows | Larger installation and graphics requirements; a browser version normally needs a render-streaming service or an export pipeline. Hosting is not automatically free. |

Epic currently states that MetaHuman is included in the Unreal Engine licence, free below US$1 million in revenue, and usable in other engines; standard terms apply above that threshold. This is a route to evaluate, not a declaration that any particular account/project, AI usage or redistribution arrangement has been cleared. No agreement was accepted, account created or MetaHuman character obtained during this task. Source: [official MetaHuman licensing page](https://www.metahuman.com/license).

Do not substitute a still photograph, pre-rendered loop or video portrait for the freely movable 3D body while marketing it as the same capability.

## Product experience

- One explicit live-conversation activation opens the microphone after browser permission. It stays available between turns. Starting to speak interrupts playback before transcription finishes.
- Display whether she is listening, thinking, speaking, quiet or waiting for a follow-up. A paused microphone and a quiet voice are different controls.
- Begin speech from a short ready phrase; prepare the following audio while the first phrase plays. Preserve the selected voice throughout.
- Let the movement persona choose suitable activity without needing a spoken instruction for every gesture. Direct instructions take priority and Stop releases the active motion.
- Follow-ups are actual saved tasks. The local prototype delivers when a studio tab is open and available; closed-app or sleeping-Mac notifications require a separate desktop scheduling service.
- Offer complete outfits and individual clothing/shoe slots. Dressing animation, garment visibility and cloth simulation must be described separately; swapping a mesh is not cloth physics.

## Proposed business model

Use a local-first base product and optional paid production assets, specialised capability packs and hosted services. Keep the character identity portable so the business is not tied to a single model provider.

Pricing experiments, not validated prices:

- Test a one-time desktop purchase against a modest monthly subscription; interview users before selecting either.
- Treat professionally authored character/outfit packs as a separate cost and licence item.
- Charge for managed cloud inference or photoreal rendering only when the per-session operating cost has been measured. Keep a working local option.
- A developer/enterprise package can provide embedding, approved character licensing, fleet controls and support after the consumer experience has been validated.

Avoid claiming a margin or user capacity before measuring speech, inference, rendering, network, storage, support and asset-licensing costs. The current local path has no model API bill, but hardware, electricity, maintenance and asset creation still cost money.

## Pilot acceptance gates

| Gate | Proposed acceptance test |
| --- | --- |
| Conversation | Ten minutes of natural discussion, with successful interruptions and no repeated Send presses or accidental self-conversation. |
| Latency | Measure microphone-to-speech-stop, end-of-user-speech-to-first-audio, transcript error rate and first-audio versus full-reply completion. Publish distributions, not a best case. |
| Visual identity | Review face close-up, profile, teeth, eyes, hair and full body under neutral light. The result should remain credible while talking and turning. |
| Movement | Test shoulder/body contact, sitting, lying/getting up, walking, dance and splits from several angles; inspect joints, grounding and intersections. |
| Wardrobe | Test every outfit and shoe combination during each motion. No floating shoes, missing body sections or exposed coverage mistakes. |
| Reliability | Interrupt synthesis, generation, transcription, a wardrobe change and a follow-up; prove old turns cannot resume later. |
| Product value | Observe whether users return voluntarily and which practical tasks they repeat. Do not confuse a visually impressive demo with willingness to pay. |

## Jarvis integration

The first adapter should expose only a small, explicit capability manifest: read a task list, query an allowed document index, prepare a draft, and request an approved action. It should return provenance and state such as proposed, drafted, completed or unavailable. Existing Jarvis communication review and trading separation remain in force.

Use an authenticated local bridge. Do not put a broker token in the avatar's public JavaScript, import trading execution modules, or let a persona's movement instructions become computer-action instructions. Autonomous movement does not imply autonomous email sending or financial execution.

Current implementation status: no Jarvis action adapter is connected. Existing local voice/model installations are reused independently.

## Immediate production work

1. Obtain/author one original production-quality adult body and face with a documented licence and the complete underlying geometry required by the character brief.
2. Author fitted underlayers, office/casual/dress outfits, actual shoe meshes and dressing/undressing clips. Verify anatomy and garment coverage in the source asset rather than inferring them from appearance.
3. Review a short benchmark of close-up talking, interruption, full-body movement and outfit changes. Choose the rendering path from that evidence.
4. Finish acoustic interruption testing on actual speakers/headphones and several microphones, then conduct a small private pilot.
5. Add the optional Jarvis adapter after the standalone experience passes those gates.
