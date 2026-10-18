# NVIDIA motion route

18 October 2026: the Mac is an Apple M1 with 16 GB unified memory. ARDY 0.2.0 and its native motion-correction extension are installed in `.runtime/ardy-venv`, separately from the studio Python, Ollama, Open WebUI and Jarvis. NVIDIA's Core motion checkpoint is downloaded and **loaded successfully on the native Mac CPU**. No Rosetta, Parallels or NVIDIA GPU was needed for that loading test.

Full text-conditioned generation is **not yet verified**. The required text-model request returned `GatedRepoError`; no Hugging Face token or authorised model cache was present. A core benchmark omits the text encoder and cannot prove prompt following or complete conversational latency. There is no model-generated movement secretly substituted with a procedural pose.

## Run the prepared pipeline

1. **Set Up NVIDIA Motion.command** installs the isolated pinned ARDY source and downloads the Core motion checkpoint. Exact source revision and tested package versions are in `ardy-manifest.json` and the private `.runtime/ardy-installed.txt` inventory.
2. Sign in to [Hugging Face's required Llama model page](https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct) and request/approve the applicable access yourself. Account creation and model agreements were not accepted in this run. **Connect NVIDIA Text Model.command** runs Hugging Face's own local sign-in and checks access; do not put a token in chat, source files or Git.
3. **Generate NVIDIA Motion.command** takes a plain-language movement description, invokes NVIDIA's real Core CLI with local text encoding and its contact correction, then converts the actual output to a self-contained animation GLB. An access/runtime failure is reported as failure, and no clip is added.
4. Add the generated GLB through the studio's Motion library and review it on the actual character. The current retargeter keeps horizontal travel in place. Scene navigation, object interaction and live streaming autoregressive integration are still required for “walk over there”. This first bridge generates offline clips; it does not claim a live ARDY-controlled persona.

The converter checks dimensions, finite values and proper rotation matrices. A separate 27-joint fixture passed real GLTFLoader parsing and retargeting to the sample; it was explicitly a test fixture and was not presented as generated motion. No benchmark or fixture is added to the user library.

A second check used actual unconditioned Core output: native inference, NVIDIA contact correction and GLB conversion completed with 40 frames, 27 joints and a 29,584-byte clip. This confirms the output schema/converter path without representing that clip as following any text instruction.

## Mac testing

Run the isolated checks with:

```sh
.runtime/ardy-venv/bin/python scripts/ardy/probe.py
.runtime/ardy-venv/bin/python scripts/ardy/benchmark_core.py --device cpu
.runtime/ardy-venv/bin/python -m unittest discover -s tests -p test_ardy_conversion.py
```

The benchmark uses genuine weights and zero text conditioning to measure only the motion core. Its JSON explicitly records that text-to-motion is unverified. The experimental `--device mps` path converts floating buffers to float32 before Metal placement. It must not be treated as equivalent to the published CUDA pipeline without validation. No source modifications to NVIDIA's repository are needed for that experimental placement.

Measured single cold runs: CPU generated 40 frames/2 seconds in **1.115 seconds**, after 2.126 seconds loading. The experimental float32 Metal run generated the same length in **3.631 seconds**, after 2.836 seconds loading. Both used the checkpoint's default 10 denoising steps and finite output checks. These are core-only timings, excluding the text encoder and contact correction; they are not warm throughput comparisons or a quality/real-time guarantee. CPU remains the prepared CLI's native Mac default.

## Existing VPS

A read-only Windows check found 2 logical processors and 4,294,410,240 bytes RAM (about 4 GiB). `nvidia-smi` was unavailable. Graphics adapter inventory through the remote keyboard was unsuccessful, so no claim is made that a GPU is physically absent. No ARDY weights, Python dependencies, services, firewall changes or listening port were installed on the trading VPS. This is an inspected server, not a deployed motion backend. The user then chose to pursue native Mac testing.

## Related NVIDIA components

- [ARDY](https://github.com/nv-tlabs/ardy): streaming text and spatially constrained motion. Published testing uses Ubuntu/RTX 4090; its CLI has a CPU fallback. Code is Apache-2.0, checkpoints have NVIDIA's model terms, and the text encoder has separate model access requirements.
- [SOMA-X](https://github.com/NVlabs/SOMA-X): shared human-body topology, rigs and shape models. A body representation is not a completed photographic skin, hairstyle, facial performance or detailed anatomical asset. Optional third-party identity backends have their own terms.
- [ProtoMotions](https://github.com/NVlabs/ProtoMotions): physics-based human motion learning. This is a separate simulation/training stack, not a browser clothing toggle.
- [NvCloth](https://github.com/NVIDIAGameWorks/NvCloth): a lower-level cloth solver. Natural dressing additionally needs garment construction, fit, collision proxies, hand contacts, authored/generated handling and quality review. It is not installed here.

[Parallels explains its GPU virtualisation](https://kb.parallels.com/en/122807); [Apple explains Rosetta's Intel translation](https://developer.apple.com/documentation/apple-silicon/about-the-rosetta-translation-environment). Neither adds NVIDIA hardware or memory. A paid hardware change should follow a complete measured Mac test rather than an assumption that installation equals useful performance.
