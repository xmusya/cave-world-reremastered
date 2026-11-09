#!/usr/bin/env python3
"""Far Lands pack: parameterize the farlands boundary with an editable
constant (data/farlands/worldgen/density_function/range.json, default 25000).
FL is already 26.3-native; we only replace in_farlands_x/z with compositional
functions referencing farlands:range, plus identity coordinate gradients."""
import os, json, shutil, zipfile

SRC = '/home/pasha/Projects/datapackgen/sources/fl'
OUT = '/home/pasha/Projects/datapackgen/build/fl263'
ZIP = '/home/pasha/Projects/datapackgen/Datapacks/Far Lands 26.3 (custom range).zip'

def wj(d, p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        json.dump(d, f, indent=2); f.write('\n')

FLAG_RAMP = "2*(abs(coord) - range) - 1, clamped to [-1,+1]"  # doc note

def flag(axis, coord_ref):
    """-1 = inside normal-ish coords, +1 = at/beyond the farlands range,
    matching the original gradient ramp width of 1 block."""
    return {
        "type": "minecraft:clamp",
        "input": {
            "type": "minecraft:add",
            "left": {
                "type": "minecraft:mul",
                "left": 2,
                "right": {
                    "type": "minecraft:sub",
                    "left": {"type": "minecraft:abs", "input": coord_ref},
                    "right": "farlands:range"
                }
            },
            "right": -1
        },
        "min": -1,
        "max": 1
    }

def identity_gradient(axis):
    # slope 1: value == coordinate. 26.3 bounds gradient from_value/to_value
    # to [-1e6,+1e6] (coordinates themselves are unbounded — original FL uses
    # 12,550,822), so use ±1,000,000. Outside the 2M span it clamps to ±1M,
    # which is still >= any allowed range, so the farlands flag stays +1.
    return {
        "type": "minecraft:gradient",
        "axis": axis,
        "tiling": "clamp_to_edge",
        "from_coordinate": -1000000,
        "to_coordinate": 1000000,
        "from_value": -1000000.0,
        "to_value": 1000000.0
    }

def main():
    if os.path.isdir(OUT): shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    df = os.path.join(OUT, 'data/farlands/worldgen/density_function')

    wj({"type": "minecraft:constant", "value": 25000.0},
       os.path.join(df, 'range.json'))
    wj(identity_gradient('x'), os.path.join(df, 'coord_x.json'))
    wj(identity_gradient('z'), os.path.join(df, 'coord_z.json'))
    wj(flag('x', 'farlands:coord_x'), os.path.join(df, 'in_farlands_x.json'))
    wj(flag('z', 'farlands:coord_z'), os.path.join(df, 'in_farlands_z.json'))

    wj(README, os.path.join(OUT, 'README - EDITING range.txt'))

    if os.path.isfile(ZIP): os.remove(ZIP)
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(OUT):
            for f in files:
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, OUT))
    print('wrote', ZIP)

README = """Far Lands 26.3 (custom range) — README
=======================================

This datapack must be installed as an UNZIPPED FOLDER datapack so you can
edit the range:

 1. Unzip "Far Lands 26.3 (custom range).zip" so that the folder containing
    pack.mcmeta sits in your world's datapacks/ directory.
 2. Reload with "/reload" (dimension changes need a world re-create or
    re-entering the dimension).

Changing the farlands range
---------------------------
Open (any text editor, e.g. Notepad):

  data/farlands/worldgen/density_function/range.json

and change the single number:

  "value": 25000.0

That is the distance from 0,0 where the Far Lands start (default 25000
blocks; vanilla Far Lands are ~12,550,821 blocks out). Range must be at
most 1,000,000 blocks. Then run /reload.
Changes to world generation only apply to newly generated chunks - chunks
you already visited keep their terrain.
"""

if __name__ == '__main__':
    main()
