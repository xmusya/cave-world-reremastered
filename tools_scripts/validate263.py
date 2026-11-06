#!/usr/bin/env python3
"""Validate the generated 26.3 overlay: JSON parse + referenced-id existence + old-format leftovers."""
import os, json, re, sys, gzip, struct

CAVE = '/tmp/opencode/cave'
O = os.path.join(CAVE, '26.3/data')
V = '/tmp/opencode/van-26.3/mcmeta-26.3-data/data/minecraft'
EFF = '/tmp/opencode/eff262/data'

def json_files(root):
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if f.endswith('.json'):
                yield os.path.join(dp, f)

errors = []; warn = []
def registry_ids(kind, ns='minecraft'):
    d = os.path.join(V, kind)
    if not os.path.isdir(d): return set()
    out = set()
    for root, _, fs in os.walk(d):
        for f in fs:
            rel = os.path.relpath(os.path.join(root, f), d)
            out.add('minecraft:' + os.path.splitext(rel)[0].replace('\\', '/'))
    return out

placed = registry_ids('worldgen/placed_feature')
features = registry_ids('worldgen/feature')
structures = registry_ids('worldgen/structure')
pools = registry_ids('worldgen/template_pool')
procs = registry_ids('worldgen/processor_list')
biomes = registry_ids('worldgen/biome')
noises = registry_ids('worldgen/noise')
dims = registry_ids('dimension_type')
cavefeat = registry_ids_ = set()
d = os.path.join(O, 'cave/worldgen/feature')
if os.path.isdir(d):
    for root, _, fs in os.walk(d):
        for f in fs:
            cavefeat.add('cave:' + os.path.relpath(os.path.join(root, f), d).rsplit('.', 1)[0])
caveplaced = set(); d = os.path.join(O, 'cave/worldgen/placed_feature')
for root, _, fs in os.walk(d or []):
    for f in fs:
        caveplaced.add('cave:' + os.path.relpath(os.path.join(root, f), d).rsplit('.', 1)[0])
cavepools = set(); d = os.path.join(O, 'cave/worldgen/template_pool')
if os.path.isdir(d):
    for root, _, fs in os.walk(d):
        for f in fs:
            cavepools.add('cave:' + os.path.relpath(os.path.join(root, f), d).rsplit('.', 1)[0])
caveprocs = set(); d = os.path.join(O, 'cave/worldgen/processor_list')
for root, _, fs in os.walk(os.path.join(O, 'cave/worldgen/processor_list')):
    for f in fs:
        caveprocs.add('cave:' + os.path.relpath(os.path.join(root, f), d).rsplit('.', 1)[0])
structnbt = set()
for ns in ('minecraft', 'cave'):
    dd = os.path.join(O, ns, 'structure')
    if os.path.isdir(dd):
        for root, _, fs in os.walk(dd):
            for f in fs:
                structnbt.add(ns + ':' + os.path.relpath(os.path.join(root, f), dd).rsplit('.', 1)[0])
# vanilla 26.3 builtin structure nbt
dd = os.path.join(V, 'structure')
for root, _, fs in os.walk(dd):
    for f in fs:
        structnbt.add('minecraft:' + os.path.relpath(os.path.join(root, f), dd).rsplit('.', 1)[0])

ALL_PLACED = placed | caveplaced
ALL_POOLS = pools | cavepools
ALL_PROCS = procs | caveprocs
ALL_FEATS = features | cavefeat

def check_refs(obj, rel):
    def rec(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ('feature', 'start_pool', 'processors', 'location') and isinstance(v, str):
                    if not v.startswith('#'):
                        if k == 'feature' and v not in ALL_PLACED and v not in ALL_FEATS and v not in placed | ALL_FEATS:
                            if v not in ALL_FEATS and v not in placed:
                                errors.append(f'{rel}: unknown feature {v}')
                        if k == 'start_pool' and v not in ALL_POOLS:
                            errors.append(f'{rel}: unknown start_pool {v}')
                        if k == 'processors' and v not in ALL_PROCS:
                            errors.append(f'{rel}: unknown processor {v}')
                        if k == 'location' and v not in structnbt:
                            errors.append(f'{rel}: unknown nbt template {v}')
                rec(v)
        elif isinstance(o, list):
            for x in o: rec(x)
    rec(obj)

# 1. all overlay json parses
d = os.path.join(O, '')
bad = 0
for p in json_files(os.path.join(CAVE, '26.3')):
    try:
        obj = json.load(open(p))
    except Exception as e:
        errors.append(f'JSON PARSE {os.path.relpath(p, CAVE)}: {e}'); continue
    check_refs(obj, os.path.relpath(p, CAVE))
    txt = open(p).read()
    for pat in ('"Name"', '"Properties"', 'random_offset', '"minCount"', '"maxCount"', 'simple_state_provider', 
                'configured_feature', '"spawners"', '"spawn_costs"', '"creature_spawn_probability"'):
        if pat in txt and 'eff/refresh' == 'never':
            pass
    # critical leftovers
    critical = []
    if '"Name"' in txt or '"Properties"' in txt: critical.append('Name/Properties')
    if '"random_offset"' in txt: critical.append('random_offset')
    if '"minCount"' in txt or '"maxCount"' in txt: critical.append('minCount/maxCount')
    if 'simple_state_provider' in txt: critical.append('simple_state_provider')
    if '"spawners"' in txt: critical.append('old spawners')
    for c in critical:
        errors.append(f'FORMAT LEFTOVER {os.path.relpath(p, CAVE)}: {c}')

# 2. biome feature arrays reference valid placed features
for p in json_files(os.path.join(O, 'minecraft/worldgen/biome')):
    b = json.load(open(p))
    for i, step in enumerate(b.get('features', [])):
        for fid in step:
            if fid.startswith('cave:') and fid not in caveplaced:
                errors.append(f'{os.path.relpath(p, CAVE)}: missing cave placed feature {fid}')
            elif fid.startswith('minecraft:') and fid not in placed:
                fn, _ = os.path.splitext(os.path.basename(p))
                errors.append(f'{os.path.relpath(p, CAVE)}: unknown vanilla placed feature {fid}')

# 3. pack.mcmeta sanity
mc = json.load(open(os.path.join(CAVE, 'pack.mcmeta')))
assert mc['pack']['min_format'] == 15, 'root min_format should be 15 (base compat)'
dirs = [e['directory'] for e in mc.get('overlays', {}).get('entries', [])]
assert '26.3' in dirs, '26.3 overlay missing'

# 4. timeline / channeling / loot spot checks
t = open(os.path.join(O, 'minecraft/timeline/day.json')).read()
if '12600' in t:
    warn.append(f'timeline still references tick 12600')
c = open(os.path.join(O, 'minecraft/enchantment/channeling.json')).read()
if '"can_see_sky": true' in c: errors.append('channeling can_see_sky not converted')
z = open(os.path.join(O, 'minecraft/loot_table/entities/zombie.json')).read()
if 'music_disc_lava_chicken' in z: errors.append('zombie still has lava chicken disc')
if '"minecraft:red_mushroom"' in z: errors.append('zombie still has red_mushroom')

print('=== ERRORS:', len(errors))
for e in errors[:120]: print(e)
print('=== WARNings:', len(warn))
for ww in warn[:40]: print(ww)
