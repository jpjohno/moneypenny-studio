#!/bin/zsh
set -e
studio_root="${0:A:h}"
cd "$studio_root"
"$studio_root/.venv/bin/python" "$studio_root/scripts/ardy/setup.py" --download-motion-model
print '\nCore setup complete. Full generation also needs authorised Hugging Face access to Meta-Llama-3-8B-Instruct. See NVIDIA_MOTION.md.'
read '?Press Return to close.'
