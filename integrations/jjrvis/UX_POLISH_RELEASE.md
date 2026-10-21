# Daily view and quieter overview

This second UX increment follows `jjrvis-performance.patch`. It keeps the mounted Moneypenny renderer and existing conversation while presenting the day in three readable sections: saved tasks/agenda, publisher headlines and connection status.

The overview is more compact, weather sits beside the daily board, and the original task-editing controls remain under Manage tasks & priorities. Existing palette and reduced-motion choices remain available. Opening the workspace stays quiet unless an introduction was explicitly requested. Our repeated setup prompt is removed; provider sign-in, macOS permission, browser-verification and message/trading review requirements remain in force.

## Install into the existing broker

1. Preserve the receiving broker and its private configuration. Apply the earlier patch chain through `jjrvis-performance.patch` only where it is not already present.
2. Compare `workspace.js`, `workspace.html` and `jarvis_comm_broker.py` with the before-file hashes in `UX_RELEASE_BASES.json`. These exact captures match the previous performance patch's resulting hashes.
3. From the receiving broker directory, check `git apply --check /path/to/integrations/jjrvis/jjrvis-ux-polish.patch`, review the small changes and apply that patch. Full owner source is intentionally absent.
4. Copy `daily-board.js`, `daily-board.css`, `workspace-polish.css` and the updated `settings-panel.js` into the existing broker. Copy the included daily-board, display-preferences and workspace-polish tests into its `tests/` directory.
5. Run the receiving broker checks and restart its existing launcher. Browser layout tests require the existing compatible Node/Chrome/Playwright installation; they skip when its prerequisites are absent. The handover records those skips explicitly rather than calling them a successful visual check.

## Data and runtime limits

Tasks and any calendar entries come only from the supplied workspace brief/snapshot. When the brief contains no calendar, the board says it has not been read and offers Open agenda. Saved task/priority read dates remain visible. An unavailable source is not displayed as an empty task list or a completed account connection.

Headlines come from the existing public news-feed endpoint. Each title links to its publisher with publication and feed-check times. The board makes at most one initial feed read, shares the result for 60 seconds across rerenders, stops a stalled read after eight seconds, and performs no background polling. Hidden/companion views defer or abort their own news read. A failed read stays explicit and does not start a retry loop.

The board does not request camera/microphone permission, read mail bodies, run a model, fetch another calendar or execute trading. Connection buttons open the existing access centre only when chosen. The account and native-device limitations documented in the performance release still apply.

`UX_VERIFICATION.json` records completed unit/syntax checks and separate desktop browser acceptance. The desktop check showed five linked publisher headlines, weather source/retrieval time, an explicit unread-calendar label, dated saved tasks/priorities, collapsed task controls and no automatic setup dialog after reload. Fullscreen, icon, hide/restore and return-to-dashboard controls passed, with no horizontal overflow or new console errors in that check. No new permission was granted; this was not an iPhone hardware or photographic-realism acceptance test.

`UX_BROWSER_VERIFICATION.json` retains those privacy-safe observations; the screenshot remains private and is not included. `UX_PUBLIC_ROUTES.json` records HTTP 200 for the new public scripts/styles and owner renderer, HTTP 401 for unauthenticated renderer access, and the existing frame/CSP/capture boundaries. No owner session cookie was issued by those route reads.

The application `tests/` Python suite passed 412 tests in 16.95 seconds. The focused root JavaScript checks passed 29 tests; the separate packaged UX checks passed 14 with two optional browser checks skipped under their available runtime. Those JavaScript scopes overlap and are not a combined total. A wider root-directory pytest collection still encounters two unrelated legacy brand/colour modules requiring the absent Pillow dependency; that wider collection is not reported as passed.

`UX_RELEASE_BASES.json` records exact before/after hashes and the successful ordinary patch-application check. `SOURCE_MANIFEST.json` covers the added helpers, tests and metadata. No runtime databases, credentials, private titles/counts, recordings or full private owner source are part of this overlay.
