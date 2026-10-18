# JJRVIS front of house integration

Source snapshot for the JJRVIS workspace already running on James's Mac. This directory is an integration handover, not a standalone server: it depends on the existing JJRVIS package and its separately stored configuration.

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

## Present limits

The current character is CG and has not passed photographic realism acceptance. The browser character is clothed. Camera permission, live house control, native phone integration, other vehicle brands and multiple household/customer records remain separate, uncompleted integration work. A phone browser cannot use another computer's localhost 3D service: the UI labels 3D as available on the Mac until a supported authenticated remote rendering route exists.

`PRODUCT_STRATEGY.md` contains the private pilot, Home Assistant integration sequence, commercial hypotheses and source links. No new customers, accounts, purchases or cameras were created.
