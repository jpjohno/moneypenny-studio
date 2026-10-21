#!/bin/zsh
set -e
studio_root="${0:A:h}"
blender_app="$HOME/Applications/Blender-4.5-LTS.app/Contents/MacOS/Blender"
anatomy_file="$studio_root/.runtime/character-workshop/Moneypenny-Adult-Anatomy-Study-v3.blend"
if [[ ! -x "$blender_app" ]]; then
  print 'Install the Blender/MPFB versions in CHARACTER_WORKSHOP.md first.'
  read '?Press Return to close.'
  exit 1
fi
if [[ ! -f "$anatomy_file" ]]; then
  python3 "$studio_root/scripts/character/setup_body_assets.py"
  if [[ ! -f "$studio_root/.runtime/character-workshop/Moneypenny-Adult-Body-Source.blend" ]]; then
    "$blender_app" --background --python "$studio_root/scripts/character/build_body_source.py" -- "$studio_root"
  fi
  "$blender_app" --background --python "$studio_root/scripts/character/refine_body.py" -- "$studio_root"
fi
exec "$blender_app" "$anatomy_file"
