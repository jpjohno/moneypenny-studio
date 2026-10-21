# Self-personality conversation routing

A request to describe the assistant’s conversational personality, ending “No device actions”, was treated as a workspace question because it contained device and actions keywords. An anchored self-personality intent now sends that narrow request to ordinary conversation. Appended inbox, file, device, web or action requests do not match this exception. The chosen saved style, answer model, voice and permissions remain unchanged.

Apply jjrvis-persona-routing.patch after jjrvis-studio-persona.patch only when the private Core matches PERSONA_ROUTING_BASES.json. Copy the updated test_studio_persona.py into the existing broker tests directory. The exact patch replay passed, along with 84 persona/Core/stream/briefing checks.

A harmless ordinary conversational question was tested against the already running broker before this routing-only restart and returned 503 after 45.1 seconds. The local uncensored 3B model was loaded at a 4K context. This confirms an additional generation/runtime delay; routing alone is not proof of working conversation. PERSONA_ROUTING_VERIFICATION.json records metadata only, without private prompt or answer content. Coordinated restart and a successful live answer remain required.

After restarting only the existing OpenWebUI chat container to clear its competing 40,960-token generations, a fresh personality question returned HTTP 200 in 18.18 seconds from uncensored-3b:latest, with local_conversation mode, model_generated provenance and the selected saved persona. Its volume was preserved; Home Assistant remained running. This is a successful reply, not a latency guarantee: the Mac remained under memory pressure.
