# Mac files and globe update — 20 October 2026

Implemented in the owner's running JJRVIS package. This is an incremental integration handover, not a standalone server or a finished customer product.

## What changed

- Fresh owner-authenticated Spotlight search of downloaded Documents, Desktop and Downloads, with explicit scope and unavailable-state messages. Sensitive names, hidden paths, dependency trees and symlinks are excluded. Opaque search handles expire after 30 minutes.
- Read-only text, Word, Excel and PowerPoint extraction. Apple PDFKit renders PDF pages as images and extracts selectable text; scanned PDFs have no OCR. Previews are bounded to 20 MB, 200 PDF pages and 60,000 extracted characters. Office macros and formulas are not executed.
- A selected-document chip and explicit Ask action carry up to 10,000 extracted characters into a focused configured AI conversation. Selection persists through answers and failures until explicitly removed or the workspace locks. No unrelated workspace records are included in document-only questions. Search and preview do not automatically send every document to a model. Original-app launches use registered absolute file paths; they do not establish app editing or saving.
- Known installed Mac applications and labelled social/YouTube website launchers. Website links do not attach accounts, read messages or authorize posting.
- The interactive Earth uses the existing full-resolution imagery through a capped 768 px WebGL surface, retaining the original coordinate mapping. GPU resources are released on disposal; unsupported or lost contexts fall back to the bounded CPU renderer. Hidden scenes pause. Static imagery is not live satellite data.

## Installation

Preserve the private package and configuration. Apply after `jjrvis-capture-rate.patch` only when the three source files match `WORKSPACE_POLISH_BASES.json`. Check and apply with `git apply --check --unidiff-zero` and `git apply --unidiff-zero`, then confirm the recorded after hashes. Copy `computer_files.py`, `globe-surface.js`, `command-scene.css`, the two included tests and `native/apple/DocumentPreview.swift` into the corresponding package locations.

On macOS, build the small PDF helper from the broker directory:

```sh
mkdir -p .runtime
swiftc native/apple/DocumentPreview.swift -o .runtime/mac-pdf-preview
```

This uses Apple's installed PDFKit and AppKit frameworks. No document files or compiled binary are distributed here. If unavailable, PDF preview explicitly falls back to opening the original application. Use the existing authenticated launcher and refresh the client. No new public exposure or account grant is created by this increment.

## Verification and limits

See `WORKSPACE_POLISH_VERIFICATION.json`. Live browser checks showed fresh search, Markdown and PDF page previews, and a selected document prepared for Ask. A synthetic PDF was visibly rendered after fixing the blank embedded viewer. A synthetic PDF question returned its exact phrase in the native app, with a source. Follow-up retained the selected file. No private document was sent to a model, and no original app document was edited. Original-app launch arguments were tested with a mock; all installed apps were not launched.

Moneypenny remains visibly CG. The existing full 3D rig, visemes, motion library, persona controls and persistent stage are retained, but photographic appearance and arbitrary human movement have not passed acceptance. The current hair source and flattened colour atlas cannot be certified as photographic through rendering changes. Unlimited computer, social-account or household autonomy is not implemented. Voice keeps the prior successful spoken-map result; this release did not repeat a new full spoken test. Use `PILOT_READINESS_20261020.md` for the measured private-pilot gates.
