#!/usr/bin/env python3
"""Generate the entropic-smoothing sculpture in Blender 3.0 or newer."""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy


RINGS = 6
SEGMENTS = 32
FRAMES = 120


def arguments():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", default="presets/original-look.json")
    parser.add_argument("--output", default="build/entropic-smoothing.blend")
    parser.add_argument("--metadata", default="build/metadata.json")
    parser.add_argument("--frames", type=int, default=FRAMES)
    return parser.parse_args(argv)


def noise(angle, radial_fraction, seed):
    """Small deterministic, continuous deformation with no random global state."""
    phase = seed * 0.61803398875
    return (
        0.55 * math.sin(3.0 * angle + phase)
        + 0.30 * math.sin(7.0 * angle - phase * 1.7)
        + 0.15 * math.sin(11.0 * angle + phase * 0.4)
    ) * math.sin(math.pi * radial_fraction)


def dome_geometry(radius, z_base, roughness, seed):
    vertices = []
    for ring in range(RINGS + 1):
        t = ring / RINGS
        r = radius * t
        # The reference is a shallow, stepped cap rather than a hemisphere.
        profile = 0.28 * radius * (1.0 - t * t) ** 0.62
        for segment in range(SEGMENTS):
            angle = 2.0 * math.pi * segment / SEGMENTS
            displacement = roughness * noise(angle, t, seed)
            vertices.append(
                (
                    (r + displacement) * math.cos(angle),
                    (r + displacement) * math.sin(angle),
                    z_base + profile + displacement * 0.35,
                )
            )

    faces = []
    for ring in range(RINGS):
        for segment in range(SEGMENTS):
            next_segment = (segment + 1) % SEGMENTS
            a = ring * SEGMENTS + segment
            b = ring * SEGMENTS + next_segment
            c = (ring + 1) * SEGMENTS + next_segment
            d = (ring + 1) * SEGMENTS + segment
            faces.append((a, b, c, d))
    faces.append(tuple(reversed([RINGS * SEGMENTS + s for s in range(SEGMENTS)])))
    return vertices, faces


def make_dome(name, radius, z_base, roughness, seed, material):
    vertices, faces = dome_geometry(radius, z_base, roughness, seed)
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def add_animation(obj, radius, z_base, roughness, seed, frames):
    obj.shape_key_add(name="Smooth")
    rough = obj.shape_key_add(name="Rough")
    rough_vertices, _ = dome_geometry(radius, z_base, roughness, seed)
    for point, coordinate in zip(rough.data, rough_vertices):
        point.co = coordinate
    rough.value = 1.0
    rough.keyframe_insert(data_path="value", frame=1)
    rough.value = 0.0
    rough.keyframe_insert(data_path="value", frame=frames)
    for curve in obj.data.shape_keys.animation_data.action.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"


def material(name, color, roughness=0.7):
    value = bpy.data.materials.new(name)
    value.diffuse_color = (*color, 1.0)
    value.use_nodes = True
    shader = value.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Roughness"].default_value = roughness
    return value


def point_camera(camera, target=(0.0, 0.0, 3.0)):
    direction = mathutils.Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def build_scene(config, frames):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    white = material("Sculpture", (0.82, 0.82, 0.82))
    strata = []
    for index in range(config["strata"]):
        radius = config["radius"] * (1.0 - 0.115 * index)
        z_base = index * config["vertical_spacing"]
        roughness = config["initial_roughness"] * math.exp(-config["decay_rate"] * index)
        obj = make_dome(
            f"Stratum_{index + 1:02d}", radius, z_base, roughness,
            config["seed"], white,
        )
        strata.append(obj)

    top = len(strata) - 1
    top_radius = config["radius"] * (1.0 - 0.115 * top)
    add_animation(
        strata[top], top_radius, top * config["vertical_spacing"],
        config["initial_roughness"],
        config["seed"], frames,
    )

    bpy.ops.object.camera_add(location=(11.8, -15.8, 9.5))
    camera = bpy.context.object
    point_camera(camera, (0.0, 0.0, 3.4))
    camera.data.lens = 52
    bpy.context.scene.camera = camera

    bpy.ops.object.light_add(type="AREA", location=(-4.0, -5.0, 14.0))
    bpy.context.object.data.energy = 1350
    bpy.context.object.data.shape = "DISK"
    bpy.context.object.data.size = 8.0
    bpy.ops.object.light_add(type="AREA", location=(7.0, 1.0, 8.0))
    bpy.context.object.data.energy = 650
    bpy.context.object.data.size = 6.0

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = frames
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.025, 0.025, 0.025)
    return scene


def main():
    args = arguments()
    preset_path = Path(args.preset).resolve()
    output_path = Path(args.output).resolve()
    metadata_path = Path(args.metadata).resolve()
    config = json.loads(preset_path.read_text(encoding="utf-8"))

    required = {
        "seed", "strata", "initial_roughness", "decay_rate", "radius",
        "vertical_spacing",
    }
    missing = required.difference(config)
    if missing:
        raise ValueError("Preset is missing: " + ", ".join(sorted(missing)))

    build_scene(config, args.frames)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path))
    metadata = {
        "preset": config,
        "blender_version": bpy.app.version_string,
        "frame_start": 1,
        "frame_end": args.frames,
        "mesh": {"rings": RINGS, "segments": SEGMENTS},
        "blend_file": output_path.name,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import mathutils
    main()
