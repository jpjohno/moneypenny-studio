# JJRVIS + Moneypenny: private home concierge

Prepared 18 October 2026. This is a product proposal and implementation roadmap. Proposed integrations, prices and acceptance targets below are not claims that they are installed, commercially validated or already achieved.

## Recommendation

Build James's own installation first: one recognisable assistant, one place to see what is connected, and reliable execution of a small set of useful household tasks. Moneypenny supplies the face, persona and conversation; JJRVIS supplies context, tools and the record of what actually happened. Use Home Assistant as the device integration layer rather than rebuilding every manufacturer's connection.

The first commercial offer should be a **professionally installed, privately operated home concierge with ongoing support**. Start with busy homeowners who already own compatible smart-home equipment. Sell reduced friction and trustworthy outcomes: a morning briefing, an evening scene and a clear explanation when a device is unavailable. Visual quality attracts attention; retained daily use and affordable support determine whether the business works. A valuation cannot be inferred from the current prototype.

## What the first product should contain

- One coherent workspace: Moneypenny over a restrained world display, with news, home, calendar, devices and tasks nearby. The map must distinguish decorative geography from verified locations or live events.
- A full persona editor behind one clear entry point. Keep voice, language, manner, appearance and supported motion configurable without changing household permissions.
- A compact orb/dot/pet appearance as an alternative to the human figure, sharing the same conversation, tools and history. A visible avatar is a presentation option; an agent is software executing a defined responsibility. Exporting or controlling any particular third-party app's dot remains unverified; no public embedding/control API for the current ChatGPT Work dot has been established here.
- A source and timestamp for operational answers. Use "Last reported 18:42" or "Unavailable" when current state cannot be verified. A model's acknowledgement is not a device receipt.
- A connection catalogue showing Supported, Connected, Needs sign-in, Unavailable or Planned. Users should never have to infer capability from a decorative tile.

Keep photographic character work as a separate quality track: licensed high-quality geometry, skin and hair maps, stable clothing fit, speech timing and motion review. Extra render counts cannot replace missing source detail. The current character is still CG; commercial redistribution clearance is unfinished in the project documentation.

## Technical foundation

Use the existing Mac for the private pilot. Run device discovery and time-sensitive household actions on the home network. An optional VPS can later carry authenticated remote coordination; it should not become a dependency for turning on a local light. Preserve the existing separation between communications and J-NEXUS trading execution.

Add a JJRVIS tool adapter to Home Assistant's supported API. Home Assistant now exposes an MCP interface for state and control. Configure a selected LLM API and a small exposed entity set instead of accepting the broad default access. Its MCP documentation describes both access configuration and current feature limitations. [Home Assistant MCP](https://www.home-assistant.io/integrations/mcp_server/), [entity exposure](https://www.home-assistant.io/voice_control/voice_remote_expose_devices/).

Keep the chosen local Ollama chat model available for conversation. Route household instructions through validated tool calls and explicit device names. Test the actual model for tool correctness before allowing direct control; an "uncensored" label says nothing about that reliability. Home Assistant calls local-model control experimental, requires tool-capable models and recommends fewer than 25 exposed entities for initial experiments. API fallback can be an optional, visible route with a budget and a defined data scope. [Ollama integration](https://www.home-assistant.io/integrations/ollama/).

Give one assistant a small set of role-scoped specialist workers: home state/actions, calendar/tasks, news/research, vehicle status and code maintenance. Each receives only its relevant tools and returns evidence to JJRVIS. These can begin as ordinary modules; additional autonomous processes are justified only where they improve measured reliability. A playful dot can show worker progress without becoming another disconnected chat.

Separate `person_id` (a real user and permissions), `persona_id` (assistant presentation), `household_id` and `device_id`. Begin with James only. Two explicitly labelled local test profiles can later prove that memories and permissions stay separate; they must not appear as real customers or live connections. Each household should eventually have its own credentials, data store, backups and audit trail. Keep credentials out of avatar prompts and browser storage.

After James's pilot, invite at most two test households initially. Treat them as separate tenants from the first real record: distinct authentication, household-bound queries, credential storage, event streams and backup/export paths. Prove cross-tenant rejection with meaningful tests before onboarding either home.

## Integration sequence and proof

| Phase | Deliverable | Acceptance evidence required |
| --- | --- | --- |
| 1. James's desk | Combined workspace, editable Moneypenny, local chat, interruptible voice, real news/task sources | Log 50 ordinary requests; review failures. Measure first audible response, interruption delay and lip timing rather than claiming instantaneous speech. |
| 2. One room | One light, one supported temperature source and one evening scene through Home Assistant | 20 consecutive device requests with confirmed state; clear unavailable response when a device or network is disconnected. Target, not current result. |
| 3. iPhone | Authenticated mobile view, phone microphone and one Assist shortcut | Test on James's actual iPhone on Wi-Fi and away from home, including permission denial, expired sign-in and Stop. |
| 4. One camera | One owner-authorised camera tile and on-demand still-image explanation | Verify stream, freshness, camera-off behaviour and recording choice. Then test a second camera. No camera activation is part of this document. |
| 5. Vehicle status | One model-specific, manufacturer-supported telemetry connection | Verify account, region, vehicle eligibility, data timestamps and recurring costs. Label unsupported commands unavailable. |
| 6. Household pilot | Two test identities, then invited real household members | Prove private history separation and role-scoped tools before adding real members. |

### iPhone and Apple Home

The shortest documented route is Home Assistant Companion plus App Intents/Shortcuts: start Assist, submit a prompt, run a scene or open a camera. A shortcut can offer an Action button, lock-screen or home-screen entry point depending on the phone and iOS version. This provides convenient access without claiming to replace every iOS system capability. [Assist on Apple devices](https://www.home-assistant.io/voice_control/apple), [App Intents](https://companion.home-assistant.io/docs/integrations/siri-shortcuts/).

HomeKit Bridge publishes selected Home Assistant entities into Apple's Home app. Matter is useful for compatible devices, but it is not universal compatibility: commissioning, local IPv6/mDNS and sometimes a Thread border router are required. Prefer existing supported equipment before buying hardware. [HomeKit Bridge](https://www.home-assistant.io/integrations/homekit/), [Matter](https://www.home-assistant.io/integrations/matter/), [Apple Matter support](https://support.apple.com/en-au/102135).

### Cameras and vehicles

Home Assistant's Generic Camera supports configured snapshot/stream sources, including RTSP. A working picture is only the first step; live analysis and event retention are separate features with separate resource needs. Start with an on-demand view. [Generic Camera](https://www.home-assistant.io/integrations/generic).

The BMW problem has a documented external cause: Home Assistant's official alert says BMW blocked the legacy ConnectedDrive API on 29 September 2025. BMW CarData is a route to approved telematics data, not evidence of unrestricted remote vehicle control. Check James's exact UK account and vehicle before promising any capability. Keep a separate status adapter so vehicle failure cannot break the rest of the house. [BMW integration alert](https://alerts.home-assistant.io/alerts/bmw_connected_drive/), [BMW CarData](https://www.bmwgroup.com/en/general/regulations/cardata.html), [customer API specification](https://bmw-cardata.bmwgroup.com/customer/public/api-specification).

Other brands need the same check. Tesla, for example, documents a Fleet API for data and commands and a pay-per-use model; it demonstrates feasibility, not free universal car support. [Tesla developer platform](https://developer.tesla.com/).

## Commercial offer and economics to test

**Pricing hypotheses, not market evidence:** a fixed-scope installation at £1,500–£3,000 plus £99–£199 per household per month for defined maintenance, updates, backups and support hours. Hardware, travel and unusually complex integrations should be quoted separately. Prototype development remains free of new subscriptions and purchases under James's current instruction.

Start by testing willingness to pay for a small dependable package. At an illustrative £149/month, assumed £15 API/hosting cost and £30 allocated support cost leave £104 before fixed development, administration, tax and acquisition costs. Those inputs must be replaced by measured pilot costs; installation profit must include all engineer hours and revisits. Avoid unlimited support or unlimited model usage.

For context, the official UK Home Assistant Cloud price is £6.50/month or £65/year including VAT. Our higher proposed price would have to earn its place through installation, the integrated experience and support; access to existing home automation alone is insufficient differentiation. [Nabu Casa pricing](https://www.nabucasa.com/pricing/).

Track weekly active households, successfully completed tasks, repeat use of the three core routines, support minutes per home, recurring gross contribution and cancellations. Do not extrapolate to millions of pounds until retention, service cost and paid demand are demonstrated.

## First marketing experiment

1. Use James's installation to record a 90-second demonstration of three real outcomes: brief my day, set this room for the evening, and show what is unavailable. Include interruption and recovery, not just a polished avatar.
2. Interview five suitable homeowners and two established home-technology installers. Validate their current frustration, installation complexity and willingness to pay. No outreach is authorised or sent by this document.
3. Invite a small fixed-scope paid pilot only after the private acceptance evidence exists. Publish an explicit compatibility list and the support boundaries.
4. Compare a character-led demonstration with a simple orb interface. Measure whether either improves task completion and return use; do not assume a human figure suits every household.
5. Use successful installations and installer referrals as the initial channel. Broader advertising and hospitality/yacht packages come after the household package can be installed repeatedly at a predictable margin.

Candidate positioning: **"One calm conversation for your home, day and devices—with clear confirmation of what happened."**

Use an original public brand and visual language before commercial launch. Record redistribution rights for each character, texture, voice and model version. For a Llama 3.2-derived deployment, the published licence has distribution, attribution and acceptable-use terms; a local model label does not replace that review. [Official Llama 3.2 licence](https://github.com/meta-llama/llama-models/blob/main/models/llama3_2/LICENSE).

## Next implementation decision

Finish the coherent private workspace, then prove one Home Assistant room and James's iPhone. Add a camera and BMW telemetry only after their exact supported routes are confirmed. That sequence gives the product a useful, testable foundation and keeps speculative integrations from delaying the first working installation.
