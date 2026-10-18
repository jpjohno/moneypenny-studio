#!/bin/zsh
set -e
studio_root="${0:A:h}"
ardy_hf="$studio_root/.runtime/ardy-venv/bin/hf"
ardy_python="$studio_root/.runtime/ardy-venv/bin/python"
if [[ ! -x "$ardy_hf" ]]; then
  print 'Open Set Up NVIDIA Motion.command first.'
  read '?Press Return to close.'
  exit 1
fi
print 'First create/sign in to your Hugging Face account and obtain access here:'
print 'https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct'
print 'Then sign in below using Hugging Face’s own command-line tool. Enter your token only in this local terminal.'
"$ardy_hf" auth login
"$ardy_python" - <<'PY'
from huggingface_hub import hf_hub_download
from huggingface_hub.errors import GatedRepoError
try:
    hf_hub_download('meta-llama/Meta-Llama-3-8B-Instruct','tokenizer_config.json')
    print('Required model access verified. Open Generate NVIDIA Motion.command for the full test; its first run downloads the encoder weights.')
except GatedRepoError:
    print('The account still needs approval for this model. No generated motion is ready yet.')
PY
read '?Press Return to close.'
