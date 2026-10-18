#!/bin/zsh
set -e
studio_root="${0:A:h}"
blender_app="$HOME/Applications/Blender-4.5-LTS.app/Contents/MacOS/Blender"
character_file="$studio_root/.runtime/character-workshop/Moneypenny-Performance-Final-Fit-v3.blend"
if [[ ! -x "$blender_app" ]]; then
  print 'Install Blender and MPFB as described in CHARACTER_WORKSHOP.md first.'
  read '?Press Return to close.'
  exit 1
fi
if [[ ! -f "$character_file" ]]; then
  print 'The local performance source has not been built. See CHARACTER_WORKSHOP.md for the build steps.'
  read '?Press Return to close.'
  exit 1
fi
exec "$blender_app" "$character_file"
