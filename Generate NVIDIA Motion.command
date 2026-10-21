#!/bin/zsh
set -e
studio_root="${0:A:h}"
ardy_python="$studio_root/.runtime/ardy-venv/bin/python"
if [[ ! -x "$ardy_python" ]]; then
  print 'Open Set Up NVIDIA Motion.command first.'
  read '?Press Return to close.'
  exit 1
fi
print 'Uses the genuine ARDY text encoder and motion model. The first generation may load large weights. CPU speed and full character quality are not yet verified.'
read 'motion_description?Describe the movement: '
[[ -n "$motion_description" ]] || exit 0
motion_output="$studio_root/.runtime/ardy-outputs/motion-$(date +%Y%m%d-%H%M%S).glb"
if "$ardy_python" "$studio_root/scripts/ardy/generate.py" "$motion_description" 5 "$motion_output"; then
  print "Animation saved: $motion_output"
  print 'Add this GLB in Moneypenny’s Motion library, then review the retargeted body and foot contact.'
else
  print 'Generation did not complete. No finished motion has been added to the studio. See NVIDIA_MOTION.md for text-model access and runtime setup.'
fi
read '?Press Return to close.'
