# Conversation and connection UX — 20 October 2026

Apply `jjrvis-conversation-ux.patch` after `jjrvis-scene-repair.patch` using `git apply --unidiff-zero`. Check CONVERSATION_UX_RELEASE_BASES.json first. Copy the updated scene-layout.js, command-scene.css, apple-setup.js and test helpers into the broker. Studio changes are regular repository source. Restart the existing services.

Start conversation explicitly arms the microphone and gives one invitation after recognition starts. Listening, microphone-off and Stop controls are visible. Existing persistent Stop and permission boundaries remain. Basic news, market, mail, Messages, WhatsApp and map requests open the relevant presenter directly. Narration is opt-in; an explicit read request enables it. Unavailable sources are not invented or read as live data.

Map & journeys reuses the existing map surface and keeps the avatar mounted. The flat map keeps its height when the globe canvas is hidden. It supports browsing without a location grant, with reported-device timestamps retained. The old location-only black map is no longer the drawer content. Briefing and overview drawers close each other.

Connections starts with clear choices for mail, phone pairing, microphone/camera checks, home, music and AI. Opening it does not grant any access. Existing sign-in and Apple permissions remain explicit.

The Mac WKWebView handles media requests only from its trusted main-frame origins and prompts through Apple; other origins and frames are denied. Source was built, signed with the existing development identity and installed locally. The owner unlocked the app; its microphone permission prompt, spoken invitation, listening state and Stop-to-microphone-off transition were verified. A dictated-question round trip remains unverified. This is not a notarized distribution release or App Store publication.

The clothed local v29 character has a matte crepe blouse and four palettes. Studio and embedded appearance share a small allowlisted local settings file; the broker proxy is GET-only and owner-protected. Scripts `scripts/character/refine_blouse_v28.py` and `refine_blouse_v29.py` reproduce garment refinement from the separately preserved local v27 Blender source. Run the v29 script with Blender background mode and the repository root after `--`; it refuses to overwrite an existing v29 export. No original Blender file is overwritten. Runtime GLBs, Blender sources, account data, build outputs and screenshots are excluded from Git. This is a garment improvement, not photographic realism.

## Verified and pending

- Broker Python suite: 415 passed. A further new appearance-boundary test also passed (35 focused proxy tests).
- Browser/voice suite: 39 passed. Final layout-only run: 10 passed at desktop/phone fixture sizes.
- Studio Python suite: 65 passed, 2 skipped. JavaScript suite: 53 passed before the additional palette test; both wardrobe tests passed after it. Syntax checks passed.
- Browser microphone check and explicit conversation startup passed; listening and Stop were verified, then capture was stopped. Native app startup and Stop were separately verified after unlock; a dictated-question round trip and real-device iPhone acceptance remain unverified.
- Live narrow workspace shows the v29 garment and usable flat-map tiles. Native app is unlocked; microphone startup and Stop were verified.
- Provider sign-ins, Messages service privacy access, missing broker ticks and BMW location remain separate connection limits. No messages, trades or payments were made.
