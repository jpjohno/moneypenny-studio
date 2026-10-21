# Performance, companion and connections increment

Verified source handover for the existing single-owner JJRVIS installation. The final incremental patch was applied to private temporary copies of all six exact source bases; every resulting file matched the final source hash. This is not a standalone server or proof that every external account is connected.

## Included behaviour

- The conversation can begin speaking completed phrases while the answer continues. The embedded character consumes the same generated audio instead of running a second voice synthesis job. Stop and reply identifiers protect newer playback from older completions.
- The globe uses a cached sphere surface and a small bundled historical NASA Earth texture. Its shading is decorative; it is not a live satellite or weather image.
- Companion mode reuses the mounted assistant. It can return to the dashboard, shrink to a movable icon, hide or open a separate browser window. A browser popup is not an operating-system overlay or guaranteed always-on-top window.
- Your connections brings Internet, Mac, iPhone, email, iCloud, camera, microphone and AI status into one centre. Public search is available when requested; it does not sign into unrelated websites.
- Mail sign-in remains per provider. Apple readiness uses existing credentials for bounded inbox-count checks and reads local Mail/Messages counts without changing read flags. Local database access does not prove cloud sync or message delivery.
- Device pairing is for the owner's own browsers. A paired browser session does not prove that an iPhone app is installed or online. The existing restricted tester preview remains separate.
- The same-origin `/presence/` renderer is available only to an authenticated owner. It reads an allowlisted set of assets from the fixed loopback Studio, without forwarding owner credentials or permitting Studio writes. The presentation child cannot use the camera, microphone or location.
- Camera and microphone checks require an explicit click, stay local in the browser and stop after 15 seconds or when the centre closes. Browser permission does not grant access to another device.

## Applying the increment

Preserve the receiving broker and private configuration first. Retain the existing `jjrvis-integration.patch`, `jjrvis-release.patch` and `jjrvis-core-recovery.patch` chain; do not reapply changes already present. Compare the receiving six source files with `PERFORMANCE_RELEASE_BASES.json` before applying this increment. Its exact before-file hashes refer to captured source, not a reconstructed baseline.

`jjrvis-performance.patch` contains one line of surrounding context for the workspace, broker, Core and answer-stream test changes. Full owner source is intentionally absent. From the receiving broker directory, run `git apply --check /path/to/integrations/jjrvis/jjrvis-performance.patch`, review the changes, then apply it. The sixth capture is the test file `tests/test_answer_stream.py`; there is no separate `answer_stream.py` module. Copy the helper, stylesheet, script, manifest, icon and test files only into their corresponding existing broker locations, then run the receiving installation's tests before restarting its own launcher.

Required new front-end helpers include `spoken-reply.js`, `globe-surface.js`, `globe-surface.css`, `globe-earth.jpg`, `apple-setup.js`, `apple-setup.css`, `companion.js` and `companion.css`. Keep `globe-surface-source.json` with the texture for attribution. The owner renderer and readiness routes require `presence_proxy.py` and `apple_connections.py` alongside the existing provider-account module. The release manifest also includes the provider UI, PWA files/icons and their focused tests. All eight newly served direct file references were checked against the handover; none are intentionally omitted.

The Studio service keeps loopback binding and private logs. Its updated launcher reloads Interactive scheduling and retries a bounded transient launchd reload race. It does not install a tunnel, buy a service, request a new permission or change the selected assistant voice/model.

## Evidence and limits

`PERFORMANCE_VERIFICATION.json` records neutral TTS route measurements, one final Mac browser sample and the completed automated suites. The final sample reached first text at 2.648 seconds, the same avatar's audio-start acknowledgement at 5.535 seconds and the validated answer at 7.267 seconds. This is one observed Mac run, not zero latency, a guarantee for other questions or a calibrated measurement of sound reaching the listener. The earlier 7.094-second first-voice / 12.533-second completed-answer sample predates the final first-phrase adjustment.

The earlier five-word generation took 0.820 seconds through the broker and 3.024 seconds through the old Studio route. Those separate synthesis measurements describe the prior route comparison and must not be presented as the new conversation's first-speech timing. The final completed suites passed 412 broker Python tests, 64 Studio Python tests with two skips, and 51 Studio JavaScript tests, plus Studio syntax checks.

`PERFORMANCE_PUBLIC_VERIFICATION.json` records HTTPS checks: the public workspace shell returned 200, unauthenticated renderer access returned 401, authenticated owner rendering and quick status returned 200, and owner Apple readiness returned 200. The render child allowed its internal blob textures while denying camera/microphone capture. These checks did not exercise actual iPhone hardware or prove that all personal integrations are connected.

The character remains CG. Photographic realism, perfect mouth timing and arbitrary human motion have not been established. Source asset and voice-model redistribution rights remain separate from this source overlay; no model weights, voice weights, character GLBs, recordings, credentials, runtime databases or private account counts are included.

The main JJRVIS LaunchAgent still reports local Mac Mail and Messages as needing macOS access. Permissions belong to the process hosting JJRVIS: successful reads from a standalone Codex process do not prove daemon access. The owner must approve the appropriate process in macOS before those connections can be labelled ready. This release does not grant or bypass that permission.

The long neutral public-search probe received a DuckDuckGo HTTP 202 browser-verification challenge and produced no sources. A short site-specific diagnostic returned HTTP 200 and ten links, confirming that normal results can still be parsed. This does not establish that every search works. JJRVIS now recognises the challenge, explains the required browser verification and offers an explicit Open search in browser link. It does not bypass the challenge, retry automatically, invent sources or switch to unrelated results. See `PERFORMANCE_WEB_VERIFICATION.json` and the two regression tests in `tests/test_web_challenge.py`.

The iPhone path is a secure web app, not native device control. iCloud Mail does not connect Photos, Drive, Health, HomeKit or iMessage cloud access. Supported folder selection is limited to the browser visit and does not claim persistent indexing. Photos and Drive links open Apple's own apps without granting their contents to JJRVIS. Additional mailboxes still require the owner to complete the provider's sign-in. Public web results may be unavailable; configured cloud keys do not prove paid API access was exercised.

## Source attribution

The new connection and companion interfaces are original project code. Browser capability checks use the platform APIs already available in the user's browser, without an external SDK.

`globe-earth.jpg` is the historical [NASA Blue Marble composite](https://science.nasa.gov/earth/earth-observatory/the-blue-marble-true-color-global-imagery-at-1km-resolution/). Credit: NASA Goddard Space Flight Center; Reto Stöckli, Robert Simmon, MODIS science teams and supporting USGS/NOAA data. Its source URL, date, dimensions, SHA-256 and credit are in `globe-surface-source.json`. Retain that attribution and follow [NASA's image/media guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/); no NASA endorsement is implied. This is informational Earth imagery, not a NASA logo or a live data feed.

The iPhone installation copy follows [Apple's Home Screen and web app instructions](https://support.apple.com/guide/iphone/iph42ab2f3a7/ios). The iCloud Mail setup points to [Apple's app-specific password instructions](https://support.apple.com/en-gb/102654), which require two-factor authentication. The included links to [iCloud Drive](https://www.icloud.com/iclouddrive/) and [iCloud Photos](https://www.icloud.com/photos/) are website handoffs, not an Apple data API connection. No Apple SDK, artwork or user photographs are redistributed by this increment.

Existing Open-Meteo, Kokoro, character asset and provider terms remain unchanged. The earlier commercial-weather and separate-customer-account limitations in the main README still apply.
