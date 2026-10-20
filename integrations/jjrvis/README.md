# Latest repair

See [SCENE_REPAIR_RELEASE.md](SCENE_REPAIR_RELEASE.md) for the assistant stage, map controls, message bodies, profile drawer and current connection blockers. Apply its patch after the native briefing increment.

# JJRVIS front of house integration

Source snapshot for the JJRVIS workspace already running on James's Mac. This directory is an integration handover, not a standalone server: it depends on the existing JJRVIS package and its separately stored configuration.

The 18 October incremental release adds an isolated tester preview, local Jarvis voice, weather and sky, clearer app permissions, and selectable light/dark palettes. It preserves the earlier v27 integration patch rather than replacing the owner's full broker source.

A further performance, companion and Apple connections increment is included as `jjrvis-performance.patch`. See `PERFORMANCE_APPLE_RELEASE.md`, `PERFORMANCE_RELEASE_BASES.json` and `PERFORMANCE_VERIFICATION.json` for its exact six-file source basis, verified patch application, included helpers and limits. Apply this increment only after the existing patch chain and only when the receiving source matches the recorded bases; the earlier patches remain intact.

The following daily-board and quieter-overview increment is `jjrvis-ux-polish.patch`. Apply it after the performance patch using `UX_RELEASE_BASES.json`; all three before hashes match that earlier patch's output. `UX_POLISH_RELEASE.md` lists its required helpers, saved-versus-current data labels, bounded news read and unchanged permission/provider review requirements.

The 19 October command-scene increment is `jjrvis-command-scene.patch`, applied after the UX patch using `COMMAND_RELEASE_BASES.json`. It adds dark startup, a larger layered world, compact navigation disclosures, read-only local/UTC clock and device status, and explicit drawers for the existing daily/weather/device views. `COMMAND_SCENE_RELEASE.md` lists required helper copies, fixture checks and remaining live/device limits.

The 20 October native preview and briefing increment is `jjrvis-native-briefing.patch`. Apply it after the command-scene patch, following `NATIVE_BRIEFING_RELEASE.md` and `NATIVE_BRIEFING_RELEASE_BASES.json`. It keeps the character loaded across workspace navigation, adds guided source cards and device onboarding, and includes shared native Apple client source. Distribution signing, real-device acceptance and payments remain pending.

The running package is `outputs/communication_broker` in the JARVIS project. Its owner workspace is http://127.0.0.1:8766/workspace ; Moneypenny runs at http://127.0.0.1:8090/ . Synced `sources/` files are read-only.

## Included changes

- The live Moneypenny stage and real interactive device atlas share one background at the top.
- Customise Moneypenny opens the full existing persona editor. Its voice, appearance, motion library and saved personas are retained.
- The embedded character has real transparency, capped Retina rendering and readiness messages from the avatar and lip engine.
- Voice messages use per-reply IDs; Stop and late completion cannot end a newer reply.
- Authenticated `/v1/workspace/connections` checks installed local model availability, local studio and saved device/vehicle configuration. It does not generate a reply, make a paid model call, activate cameras or control vehicles.
- Local Ollama and optional configured cloud routing stay explicit. Credentials and runtime are excluded.
- J-NEXUS recorder and execution authority remain in their existing package.

Preserve the current broker package, check and apply `jjrvis-integration.patch` against its v26 workspace files, then copy `connection_status.py` and the tests into their matching locations. Restart that package with its existing launcher. The patch records only this integration; unrelated personal workspace source, configuration and runtime are excluded. This is not a migration or replacement for the rest of the broker.

## Incremental release installation

1. Preserve the existing broker and its private configuration. Apply `jjrvis-integration.patch` first only if the receiving broker is still at the earlier v26 integration basis. Do not reapply it to an already integrated v27 workspace.
2. Compare the receiving `jarvis_comm_broker.py`, `workspace.js`, `workspace.html` and `workspace.css` hashes with `RELEASE_BASES.json`. From that broker directory, run `git apply --check /path/to/integrations/jjrvis/jjrvis-release.patch`, review its small source differences, then apply the patch. The release patch uses one line of context and expects the recorded v27 basis; it does not contain or replace the full private owner application. Then compare the core, mail-reader and core-test hashes with `CORE_RELEASE_BASES.json`, check and apply `jjrvis-core-recovery.patch` in the same way. This second patch contains only the bounded home-read, explicit web-search and cached-mail recovery changes plus their tests; its basis is reconstructed from the exact final edits rather than an independent historical capture.
3. Copy the included `tester_preview.py`, `sky_weather.py`, `lifestyle.js`, `lifestyle.css`, `settings-panel.js`, `settings-panel.css`, `voice_profiles.py`, `local_voice.py`, `local_voice_worker.py`, `cloud_ai.py` and `connection_status.py` into the broker directory, and the included test files into its `tests/` directory. `release-styles.css` is a reference overlay only: the same CSS changes are already in `jjrvis-release.patch`, so no extra stylesheet route or link is needed.
4. Use the broker's existing Python 3.11+ environment and dependencies. Local Kokoro voice/model files and the selected installed Ollama model remain separate prerequisites. No voice weights, audio, personal configuration, model weights or runtime databases are included here.
5. Run the preview, release-boundary, weather, local-voice and voice-profile tests in that broker environment. Run the display-preference JavaScript tests with the receiving workspace CSS. Their optional browser checks require the existing Playwright/Chrome installation and otherwise skip. Restart using the broker's existing launcher after checks pass; this package creates no new tunnel, public host or provider account.

`SOURCE_MANIFEST.json` records the SHA-256 of each handover file. `RELEASE_BASES.json` records the required before-file hashes and explains the reconstructed CSS basis. `CORE_RELEASE_BASES.json` records the separate core/mail patch basis and successful byte-for-byte application check. Source copies are code only; test addresses, coordinates, prompts and tokens are synthetic fixtures rather than owner records.

## Restricted tester preview

The owner Projects & connections screen, under Private testing, can create a preview link for manual sharing. Creation returns a link but does not send it. The link uses `/preview#invite=...`; the browser removes the fragment immediately and requires an explicit Accept action before redeeming it.

Preview invitations expire after ten minutes and can be used once. A preview session uses a separate HttpOnly cookie and hashed-token database, lasts at most seven days without renewal, and can be revoked or disconnected. It permits bounded text conversation with a fixed local Ollama model and Moneypenny/Jarvis presentation choices. It has no owner context, mail, contacts, files, household tools, vehicle access, trading, live internet, cloud fallback or event stream. It cannot manage invitations or create owner sessions. Request, history, response, rate, concurrency and duration limits are enforced on the server.

**Owner pairing links still grant owner access.** Share only the restricted `/preview#invite=...` link with testers. Ordinary phone pairing is for the owner's own devices. Full customer accounts, separate household service credentials and cross-household connected-device support are not implemented by this limited preview.

## Weather, app links and voice

Weather remains off until a town is selected. The interface states that searches and rounded coordinates go to Open-Meteo and labels the sky artwork as decorative. Forecast validity and retrieval times are preserved. Turning weather off stops automatic forecast requests. The current free Open-Meteo endpoint is for evaluation and non-commercial prototyping; a sold service needs an appropriate commercial licence or separately reviewed self-hosting arrangement. No subscription was purchased. See [Open-Meteo terms and plans](https://open-meteo.com/en/pricing).

App shortcuts distinguish connected services, Mac-synced copies, setup requirements and website handoffs. Opening ChatGPT, a social network, a provider security page or Vonage does not attach that account or prove device control. General desktop control is not included.

Jarvis now has a local Kokoro voice alongside Moneypenny. Explicit cloud voice profiles remain separately labelled. The embedded character's mouth animation and photographic appearance still need human acceptance; successful WAV generation is not proof of perfect lip timing.

## Present limits

The current character is CG and has not passed photographic realism acceptance. The browser character is clothed. Live house control, native phone integration, other vehicle brands and multiple household/customer records remain separate, uncompleted integration work. The performance increment adds an authenticated owner-only remote renderer, without exposing Studio writes or granting its child camera/microphone access; actual iPhone hardware acceptance remains unverified. Explicit parent camera/microphone tests are local browser previews, not general device or camera integrations. The main LaunchAgent still needs process-specific macOS permission before its local Mail/Messages connections are ready, and several provider sign-ins remain unfinished.

`PRODUCT_STRATEGY.md` contains the private pilot, Home Assistant integration sequence, commercial hypotheses and source links. No new customers, accounts, purchases or cameras were created.

## Verified local conversation

The selected Sadiq uncensored 3B model returned a warmed direct response in 0.71 seconds and the full authenticated JJRVIS chat returned an arithmetic answer in 3.25 seconds. See `LOCAL_AI_VERIFICATION.json` for the bounded synthetic tests, including cold-load timeout. No paid request or device action was made. This does not guarantee cold-start latency or tool accuracy for arbitrary tasks.

`LIVE_PREVIEW_VOICE_VERIFICATION.json` records a later local loopback check: Jarvis WAV generation, unchanged selected preferences, owner and isolated-preview arithmetic answers, rejection of owner APIs from the preview cookie, one-use links, disconnect and active revocation. Both temporary test invitations were revoked. It contains no invitation link, token, account address, device identifier, personal coordinates, internal filesystem path or raw audio. External HTTPS delivery and human voice/photographic acceptance were not tested by those checks.

`PUBLIC_ROUTE_VERIFICATION.json` separately records unauthenticated HTTPS route checks: the preview shell was reachable, owner workspace data required authentication, and remote owner bootstrap was denied. This checks public route boundaries, not a complete authenticated remote session. `RELEASE_READINESS.json` records the completed automated suites and the remaining human acceptance and customer-isolation gaps.
