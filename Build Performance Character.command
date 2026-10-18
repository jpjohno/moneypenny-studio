#!/bin/zsh
set -e
studio_root="${0:A:h}"
blender_app="$HOME/Applications/Blender-4.5-LTS.app/Contents/MacOS/Blender"
cd "$studio_root"
if [[ ! -x "$blender_app" || ! -f .runtime/character-workshop/Moneypenny-Adult-Anatomy-Study-v3.blend ]]; then
  print 'Build the adult source with Build Adult Anatomy.command first. Existing scenes are preserved.'
  read '?Press Return to close.'
  exit 1
fi
.venv/bin/python scripts/character/setup_body_assets.py --performance
for character_stage in build_performance_character polish_performance_fit detail_performance_character finish_performance_fit prepare_performance_export; do
  "$blender_app" --background --python "scripts/character/$character_stage.py" -- "$studio_root"
done
if [[ ! -f .runtime/character-workshop/Moneypenny-Performance-Candidate-v6.glb ]]; then
  print 'The candidate was not completed. Preserve the logs and review CHARACTER_WORKSHOP.md.'
  read '?Press Return to close.'
  exit 1
fi
print 'Local source and candidate ready. No website character was replaced.'
exec "$studio_root/Open Performance Character.command"
