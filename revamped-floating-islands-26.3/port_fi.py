#!/usr/bin/env python3
"""Port Revamped Floating Islands (26.1-style) to Minecraft 26.3."""
import os, json, copy, shutil, zipfile

SRC = '/home/pasha/Projects/datapackgen/sources/fi'
OUT = '/home/pasha/Projects/datapackgen/build/fi263'
_ZIP = '/home/pasha/Projects/datapackgen/Datapacks/Revamped Floating Islands'
# VOID=True: "true void" variant — remove FI's ocean/river sinking and the
# sunken ocean floor, sea_level -64 (vanilla skyworld trick) so the void is
# not flooded.
VOID = False
ZIP = _ZIP + (' 26.3 (true void).zip' if VOID else ' 26.3.zip')
VOIDED = ('terrain/ocean_reduction.json', 'terrain/river_reduction.json',
          'terrain/ocean_floor.json')
# Raise the whole island band by RAISE blocks (user: islands too low,
# structures like trial chambers at y~0 should end up INSIDE islands).
RAISE = 80

def raise_shift(rel, d):
    if not RAISE or rel not in ('depth.json', 'terrain/base.json', 'terrain/ocean_floor.json'):
        return d
    s = json.dumps(d).replace('"minecraft:y"', json.dumps('@@Y@@'))
    d = json.loads(s)
    def walk(o):
        if isinstance(o, dict):
            t = o.get('type')
            if t == 'minecraft:gradient' and o.get('axis') == 'y':
                if 'from_coordinate' in o: o['from_coordinate'] += RAISE
                if 'to_coordinate' in o: o['to_coordinate'] += RAISE
            if t == 'minecraft:range_choice' and o.get('input') == '@@Y@@':
                o['input'] = {'type': 'minecraft:sub', 'left': 'minecraft:y',
                              'right': RAISE}
                o['min_inclusive'] += RAISE
                o['max_exclusive'] += RAISE
            for k, v in o.items(): o[k] = walk(v)
        elif isinstance(o, list):
            for i, x in enumerate(o): o[i] = walk(x)
        return o
    return walk(d)

def rj(p): return json.load(open(p))
def wj(d, p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        json.dump(d, f, indent=2); f.write('\n')

# ---- conversion helpers (per AGENTS.md rules, verified on Cave World) ----
def conv_state(d):
    out = {'id': d['Name']}
    if d.get('Properties'):
        out['properties'] = d['Properties']
    for k, v in d.items():
        if k not in ('Name', 'Properties'):
            out[k] = copy.deepcopy(v)
    return out

PROVIDERS = {
    'minecraft:simple_state_provider': 'simple',
    'minecraft:weighted_state_provider': 'weighted',
    'minecraft:noise_provider': 'noise',
    'minecraft:dual_noise_provider': 'dual_noise',
    'minecraft:noise_threshold_provider': 'noise_threshold',
    'minecraft:randomized_int_state_provider': 'randomized_int',
    'minecraft:rule_based_state_provider': 'rule_based',
}

def convert(obj):
    if isinstance(obj, list): return [convert(x) for x in obj]
    if isinstance(obj, dict):
        if 'Name' in obj:
            st = conv_state(obj)
            return {k: (v if isinstance(v, str) else convert(v)) for k, v in st.items()}
        t = obj.get('type')
        out = {k: convert(v) for k, v in obj.items()}
        if t in PROVIDERS: out['type'] = PROVIDERS[t]
        return out
    return obj

CACHE_TYPES = ('minecraft:flat_cache', 'minecraft:cache_once',
               'minecraft:cache_2d', 'minecraft:cache_all_in_cell',
               'minecraft:interp_cache')

def convert_df(obj):
    if isinstance(obj, list): return [convert_df(x) for x in obj]
    if isinstance(obj, dict):
        out = {k: convert_df(v) for k, v in obj.items()}
        t = out.get('type')
        # cache wrappers REMOVED in 26.3 (flat_cache/cache_once/cache_2d/
        # cache_all_in_cell — error-log-proved): inline the input.
        # All FI usages have y-independent inputs, so lossless.
        if t in CACHE_TYPES:
            return out.get('input', out.get('argument'))
        if 'argument' in out and 'input' not in out: out['input'] = out.pop('argument')
        if 'argument1' in out and 'left' not in out: out['left'] = out.pop('argument1')
        if 'argument2' in out and 'right' not in out: out['right'] = out.pop('argument2')
        if t == 'minecraft:shifted_noise':
            # 26.3: plain noise with inline shift fields
            out['type'] = 'minecraft:noise'
        if t == 'minecraft:interpolated':
            out.setdefault('cell_size_xz', 4)
            out.setdefault('cell_size_y', 8)
        if t == 'minecraft:y_clamped_gradient':
            out['type'] = 'minecraft:gradient'
            if 'from_y' in out: out['from_coordinate'] = out.pop('from_y')
            if 'to_y' in out: out['to_coordinate'] = out.pop('to_y')
            out.setdefault('axis', 'y')
        if t in PROVIDERS: out['type'] = PROVIDERS[t]
        return out
    if obj == 'minecraft:nether/base_3d_noise':
        return 'minecraft:overworld/base_3d_noise'
    return obj

def convert_spawn_target(entries):
    out = []
    mapping = {'continentalness': 'minecraft:overworld/continents',
               'erosion': 'minecraft:overworld/erosion',
               'weirdness': 'minecraft:overworld/ridges',
               'temperature': 'minecraft:overworld/temperature'}
    for e in entries:
        e = dict(e)
        for drop in ('depth', 'humidity', 'offset'):
            e.pop(drop, None)
        out.append({mapping.get(k, k): v for k, v in e.items()})
    return out

def main():
    if os.path.isdir(OUT): shutil.rmtree(OUT)
    os.makedirs(OUT)
    ns = rj(os.path.join(SRC, 'overlay_1_21_9/data/minecraft/worldgen/noise_settings/overworld.json'))

    # --- noise_settings/overworld (26.3) ---
    router = ns['noise_router']
    r = ns['router263'] if False else {}
    r['chunk_surface_level'] = 'minecraft:overworld/chunk_surface_level'
    r['continents'] = router['continents']
    r['depth'] = router['depth']
    r['erosion'] = router['erosion']
    r['final_density'] = router['final_density']
    r['ridges'] = router['ridges']
    r['temperature'] = convert_df(router['temperature'])
    r['vegetation'] = convert_df(router['vegetation'])

    ds = json.dumps(r['temperature'])
    assert 'shift' in ds and r['temperature']['type'] == 'minecraft:noise', r['temperature']

    aqu = {
        'barrier': convert_df(router['barrier']),
        'exclusion': {'type': 'minecraft:min',
                      'left': {'type': 'minecraft:sub', 'left': -0.225, 'right': 'minecraft:overworld/erosion'},
                      'right': {'type': 'minecraft:max',
                                'left': {'type': 'minecraft:sub', 'left': 'minecraft:overworld/depth', 'right': 0.9},
                                'right': 0.0}},
        'fluid_level_floodedness': convert_df(router['fluid_level_floodedness']),
        'fluid_level_spread': convert_df(router['fluid_level_spread']),
        'lava': convert_df(router['lava']),
        'surface_level': 'minecraft:overworld/preliminary_surface_level',
    }

    out_ns = {
        'aquifers': aqu,
        'default_block': convert(ns['default_block']).get('id') if isinstance(convert(ns['default_block']), dict) else convert(ns['default_block']),
        'default_fluid': convert(ns['default_fluid']).get('id') if isinstance(convert(ns['default_fluid']), dict) else convert(ns['default_fluid']),
        'disable_mob_generation': ns['disable_mob_generation'],
        'legacy_random_source': ns['legacy_random_source'],
        'material_rule': 'minecraft:overworld',
        'noise': {'min_y': ns['noise']['min_y'], 'height': ns['noise']['height']},
        'noise_router': r,
        'sea_level': -64 if VOID else ns['sea_level'],
        'spawn_target': convert_spawn_target(ns['spawn_target']),
    }
    wj(out_ns, os.path.join(OUT, 'data/minecraft/worldgen/noise_settings/overworld.json'))
    wj(convert(ns['surface_rule']), OUT + '/data/minecraft/worldgen/material_rule/overworld.json')

    # --- rfi density functions ---
    base = os.path.join(SRC, 'data/rfi/worldgen/density_function')
    for root, _, files in os.walk(base):
        for f in files:
            if f == 'desktop.ini': continue
            src = os.path.join(root, f)
            rel = os.path.relpath(src, base)
            if VOID and rel.replace(os.sep, '/') in VOIDED:
                d = {'type': 'minecraft:constant', 'value': 0.0}
            else:
                d = convert_df(rj(src))
            # FIX: structure terrain adaptation — 26.3 vanilla final_density
            # adds minecraft:beardifier so jigsaw structures (trial chambers!)
            # carve/blend properly; FI's 26.1 final lacks it.
            if rel.replace(os.sep, '/') == 'terrain/final.json':
                d = {'type': 'minecraft:add', 'left': d,
                     'right': {'type': 'minecraft:beardifier'}}
            d = raise_shift(rel.replace(os.sep, '/'), d)
            # 3-band islands (user spec): main belt ~80..120 normal density;
            # sparse low band -30..60 (threshold +0.2, none below -30);
            # very sparse high band 160..256 (threshold +0.35, no fading to
            # 318); nothing outside those zones (121..159 gap, y<-30 void).
            if rel.replace(os.sep, '/') == 'terrain/base.json':
                def fade(lo, hi, v0, v1):
                    return {
                        'type': 'minecraft:gradient',
                        'axis': 'y', 'tiling': 'clamp_to_edge',
                        'from_coordinate': lo, 'to_coordinate': hi,
                        'from_value': v0, 'to_value': v1
                    }
                def band(lo_lo, lo_hi, v0, hi_lo, hi_hi, v1, thr):
                    # fade in at [lo_lo..lo_hi] 0->1, fade out at
                    # [hi_lo..hi_hi] 1->0; threshold shifts noise peak rarity
                    return {
                        'type': 'minecraft:mul',
                        'left': {
                            'type': 'minecraft:mul',
                            'left': fade(lo_lo, lo_hi, v0, 1.0),
                            'right': fade(hi_lo, hi_hi, 1.0, v1)
                        },
                        'right': {
                            'type': 'minecraft:sub',
                            'left': 'minecraft:end/base_3d_noise',
                            'right': thr
                        }
                    }
                low = band(-30, 0, 0.0, 75, 100, 0.0, 0.2)
                high = band(130, 160, 0.0, 240, 256, 0.0, 0.35)
                d = {'type': 'minecraft:add', 'left': d,
                     'right': {'type': 'minecraft:add', 'left': low,
                               'right': high}}
            s = json.dumps(d)
            for bad in ('"argument"', '"argument1"', '"argument2"', 'y_clamped_gradient',
                        '"Name"', 'shifted_noise'):
                if bad in s:
                    print('WARN leftover', rel, bad)
            wj(d, os.path.join(OUT, 'data/rfi/worldgen/density_function', rel))

    # --- pack.mcmeta ---
    mc = rj(os.path.join(SRC, 'pack.mcmeta'))
    mc['pack']['pack_format'] = 121
    mc['pack']['min_format'] = 121
    mc['pack']['max_format'] = 199
    mc['pack']['supported_formats'] = [121, 199]
    mc.pop('overlays', None)
    wj(mc, os.path.join(OUT, 'pack.mcmeta'))

    shutil.copy(os.path.join(SRC, 'pack.png'), os.path.join(OUT, 'pack.png'))

    if os.path.isfile(ZIP): os.remove(ZIP)
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(OUT):
            for f in files:
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, OUT))
    print('wrote', ZIP)

if __name__ == '__main__':
    main()
