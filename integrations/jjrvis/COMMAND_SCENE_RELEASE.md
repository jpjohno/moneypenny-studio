# Layered command scene

This increment follows `jjrvis-ux-polish.patch`. The overview becomes a single layered scene: a larger interactive Earth behind Moneypenny, a read-only local/UTC clock and device HUD, and compact Work, Connected and Explore navigation. The default opens dark before styles paint; an explicitly saved palette still wins. A legacy automatic Sky default migrates to Midnight, while an explicit light choice remains saved.

Your day, Weather & sky and Device map open as drawers. Their existing source views mount on request and retain their DOM and actions when reopened. The workbench preserves project and task controls below the scene. Companion mode uses the same character iframe, hides the dashboard instruments and returns to the dashboard with Escape.

## Apply to the existing broker

1. Preserve the receiving broker and its private configuration. Apply the earlier chain through `jjrvis-ux-polish.patch` only if those changes are absent.
2. Compare `workspace.js`, `workspace.html` and `jarvis_comm_broker.py` against `COMMAND_RELEASE_BASES.json`. Its three before hashes exactly match the preceding UX patch's after hashes. The before captures were taken from the state published with repository commit `1c16c76`; full private source is excluded here.
3. From the receiving broker directory, run `git apply --check /path/to/integrations/jjrvis/jjrvis-command-scene.patch`, review the increment and apply it. If hashes differ, reconcile the receiving source before applying; do not replace it with unrelated full application files.
4. Copy `command-deck.js`, `command-deck.css`, `command-scene.css`, `scene-layout.js`, `theme-init.js`, and the updated `settings-panel.js` and `globe-surface.js` into the broker. Retain the previously included styles, helpers and attributed Earth image. Copy the command-deck, command-scene, theme-init, display-preferences and globe-surface tests into its `tests/` directory.
5. Run the receiving application's checks, then restart its existing launcher. The production-style fixtures require compatible Node, Chrome and Playwright plus the applied broker's private workspace shell/styles. They skip when those prerequisites are absent; an unapplied overlay is not a standalone application.

The patch was checked and applied to private temporary copies of all three exact bases, and its outputs matched the final source bytes. Earlier patches remain unchanged. `SOURCE_MANIFEST.json` records the supplied file hashes.

## Data, activity and permissions

The clock uses the browser's real local time and UTC. It pauses while hidden, offscreen or in companion mode and removes its interval/listeners on destruction. The HUD itself makes no API, model or speech request. The overview reuses existing authenticated device and system metadata reads while active; it does not poll mail or inference.

Device rows come from supplied heartbeat records. Currently reporting devices lead the bounded list, followed by recent saved reports; the total includes all supplied devices. Reports older than three minutes do not appear current. Model availability is labelled as availability, rather than a successful inference test. Speech-engine readiness does not imply that microphone permission has been granted.

The Earth uses the existing attributed static imagery and reported device markers. Orbital lines, grid, glow and depth effects are decorative. They are not live satellite imagery or evidence of device control. Existing source dates and unavailable labels remain relevant inside drawers. Public web search can still require an explicit browser verification step from its provider.

No camera/microphone grant, new provider account, vehicle command, trading action or paid model call is part of this layout increment. Provider sign-in and process-specific macOS permission requirements remain in force. The character remains CG; photographic realism and native iPhone hardware acceptance are not claimed.

## Verification

`COMMAND_SCENE_VERIFICATION.json` records 13 passing source checks with no skips: eight command-module checks and five production-style fixtures. The fixtures cover 1280×800, 1440×900 and 390×844 in all five palettes; contained menus, larger Earth, telemetry bounds and contrast; 44-pixel phone targets and actual tool/pair callback clicks; keyboard/modal Escape and focus; source/button/frame preservation; and companion fullscreen/return behavior. The fixtures load no owner endpoint, avatar renderer or 3D engine and request no capture permission.

The final root run passed 39 unique broker JavaScript checks with no skips in 13.695 seconds, including the command, first-paint theme, production-layout, voice, globe and preference checks. A separate combined command/theme/layout run passed 16 checks in 10.138 seconds. These scopes overlap with the earlier 13-check run and must not be added. The application `tests/` Python suite passed 412 tests in 19.89 seconds; the separate Studio appearance suite passed 52 JavaScript checks. A wider legacy root pytest collection is not reported as passed because unrelated brand/colour modules require the absent Pillow dependency.

`COMMAND_PUBLIC_ROUTES.json` preserves public HTTP and security metadata: new helpers/styles and the authenticated renderer returned 200; unauthenticated renderer access returned 401; the parent remained unframeable and the child retained its nonce CSP and capture restrictions. Its earlier direct Node run records five browser skips; the separate compatible source-fixture run executed those checks.

`COMMAND_BROWSER_VERIFICATION.json` records completed owner-browser acceptance in a 566×647 narrow desktop pane: saved dark startup, menus, real publisher headlines, dated weather, reported device/voice details, Junomo review columns, companion fullscreen/icon/hide/restore, and lazy workbench mounting with one shared Earth and no duplicate motion control. No new page console error was observed. Final full-width desktop geometry was checked in isolated fixtures, rather than a final full-width owner session; a narrow browser pane is not physical iPhone acceptance. No private screenshot, recording, runtime database, model/audio weight, avatar asset or full private workspace source is included in this overlay.
