#!/usr/bin/env bash
set -euo pipefail

BLENDER_BIN="${BLENDER_BIN:-blender}"
PRESET="${1:-presets/original-look.json}"

mkdir -p build/frames
"$BLENDER_BIN" --background --python generate.py -- \
  --preset "$PRESET" \
  --output build/entropic-smoothing.blend \
  --metadata build/metadata.json

"$BLENDER_BIN" --background build/entropic-smoothing.blend \
  --render-output "//frames/frame_#####" \
  --render-anim

if command -v ffmpeg >/dev/null 2>&1; then
  ffmpeg -y -framerate 30 -i build/frames/frame_%05d.png \
    -c:v libx264 -pix_fmt yuv420p build/entropic-smoothing.mp4
fi
