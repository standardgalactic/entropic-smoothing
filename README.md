# Entropic Smoothing

This sculpture represents entropy-gradient smoothing as a sequence of dome-like
strata. Every stratum begins with the same radial form and deterministic noise
field. Its deformation amplitude follows
`initial_roughness * exp(-decay_rate * stratum)`, so the sequence becomes
progressively smoother without changing its underlying construction.

The original `entropic_smoothing.blend` and `preview.png` remain the visual
reference. `generate.py` provides a reproducible approximation rather than
claiming vertex-for-vertex recovery of the original scene.

## Generate and render

Blender 3.0 or newer is required. Run:

```bash
./render.sh
```

The script creates `build/entropic-smoothing.blend`, `build/metadata.json`, and
120 PNG frames. If `ffmpeg` is installed, it also creates an H.264 MP4. Set
`BLENDER_BIN` when Blender is not on `PATH`, or pass another preset as the first
argument.

```bash
BLENDER_BIN=/opt/blender/blender ./render.sh presets/original-look.json
```

The upper dome animates from the preset's initial roughness to a nearly smooth
state. The footprint, camera, lighting, and other strata remain fixed, making
the changing surface directly comparable between frames. Reusing the same seed
and preset produces the same mesh.

## Preset parameters

`presets/original-look.json` exposes the seed, number of strata, initial
roughness, exponential decay rate, base radius, and vertical spacing. Fixed
mesh and render details are intentionally kept in the generator until the
visual reconstruction has stabilized.
