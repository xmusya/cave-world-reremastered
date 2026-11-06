#!/usr/bin/env python3
"""Generate the Cave World Remastered 26.3 (pack format 121.0) overlay."""
import os, json, shutil, gzip, copy, struct, sys

CAVE = '/tmp/opencode/cave'
EFF = '/tmp/opencode/eff262/data'
V263 = '/tmp/opencode/van-26.3/mcmeta-26.3-data/data'
OUT = os.path.join(CAVE, '26.3')

warnings = []
def warn(msg):
    warnings.append(msg); print('WARN:', msg)

def rj(p): return json.load(open(p))
def wj(d, p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write('\n')

# ------------------------------------------------------- block states/providers
RENAMED_PROVIDERS = {
    'minecraft:simple_state_provider': 'simple',
    'minecraft:weighted_state_provider': 'weighted',
    'minecraft:noise_provider': 'noise',
    'minecraft:dual_noise_provider': 'dual_noise',
    'minecraft:noise_threshold_provider': 'noise_threshold',
    'minecraft:randomized_int_state_provider': 'randomized_int',
    'minecraft:rule_based_state_provider': 'rule_based',
}

def conv_state(d):
    out = {'id': d['Name']}
    if d.get('Properties'):
        out['properties'] = d['Properties']
    for k, v in d.items():
        if k not in ('Name', 'Properties'):
            out[k] = copy.deepcopy(v)
    return out

def convert(obj):
    if isinstance(obj, list):
        return [convert(x) for x in obj]
    if isinstance(obj, dict):
        if 'Name' in obj:
            st = conv_state(obj)
            return {k: (v if isinstance(v, str) else convert(v)) for k, v in dict(st).items()}
        otype = obj.get('type')
        if otype == 'minecraft:simple_state_provider':
            return convert(obj.get('state'))
        out = {k: (convert(v) if not isinstance(v, str) else v) for k, v in obj.items()}
        if otype in RENAMED_PROVIDERS:
            out['type'] = RENAMED_PROVIDERS[otype]
        return out
    return obj

# ------------------------------------------------------------------- features
def conv_feat(f):
    """old configured-feature (inline) -> 26.3 bare feature object"""
    if isinstance(f, str):
        return f
    f = copy.deepcopy(f)
    t = f.pop('type')
    cfg = f.pop('config', {})
    out = {'type': t}
    if t == 'minecraft:random_selector':
        feats = cfg.get('features', [])
        default = cfg.get('default')
        p_left = 1.0
        margs = []
        for x in feats:
            ch = x.get('chance', 0.0)
            margs.append((x, ch * p_left))
            p_left *= (1 - ch)
        margs.append((default, p_left))
        entries = []
        for x, p in margs:
            w = max(1, int(round(p * 1000)))
            inner = x['feature']
            if isinstance(inner, dict) and isinstance(inner.get('feature'), (dict, str)):
                feat = conv_feat(inner['feature'])
                placement = inner.get('placement', [])
            else:
                feat = conv_feat(inner)
                placement = x.get('placement', [])
            entries.append({'data': {'feature': feat, 'placement': placement}, 'weight': w})
        out = {'type': 'minecraft:weighted_random_selector', 'features': entries}
        return out
    out.update(convert(cfg))
    return out

# -------------------------------------------------------------------- placed
def trapezoid(v):
    if isinstance(v, (int, float)):
        if v == 0:
            return 0
        return {'type': 'minecraft:trapezoid', 'min': -abs(v), 'max': abs(v), 'plateau': 0}
    return v

def convert_placed(obj):
    obj = copy.deepcopy(obj)
    def walk(d):
        if isinstance(d, list):
            return [walk(x) for x in d]
        if isinstance(d, dict):
            if d.get('type') == 'minecraft:random_offset':
                out = {'type': 'minecraft:offset'}
                for axis in ('x', 'y', 'z'):
                    v = d.get(axis + '_spread', 0)
                    out[axis] = walk(v) if isinstance(v, (dict, list)) else trapezoid(v)
                return out
            return {k: walk(v) for k, v in d.items()}
        return d
    return convert(walk(obj))

# --------------------------------------------------------------------- biome
def count_of(mn, mx):
    if mn == mx:
        return mn
    return {'type': 'minecraft:uniform', 'min_inclusive': mn, 'max_inclusive': mx}

def convert_biome(obj, name=''):
    b = copy.deepcopy(obj)
    spawns = b.pop('spawners', None)
    costs = b.pop('spawn_costs', {})
    prob = b.pop('creature_spawn_probability', None)
    if prob is not None:
        b.setdefault('attributes', {})['minecraft:gameplay/creature_world_gen_spawn_probability'] = prob
    if spawns is not None:
        arg = {'spawn_costs': costs or {}, 'spawns_by_category': {}}
        for cat, lst in spawns.items():
            if not lst:
                continue  # vanilla 26.3 omits empty categories
            arg['spawns_by_category'][cat] = [
                {'type': e['type'], 'count': count_of(e.get('minCount', 1), e.get('maxCount', 1)), 'weight': e['weight']}
                for e in lst]
        b.setdefault('attributes', {})['minecraft:gameplay/natural_mob_spawns'] = arg
    return convert(b)

# ----------------------------------------------------------------- structures
def convert_structure(obj):
    s = copy.deepcopy(obj)
    so = s.get('spawn_overrides')
    if isinstance(so, dict):
        new = {}
        for cat, val in so.items():
            if isinstance(val, dict) and 'spawns' in val:
                raw = val['spawns']
                if isinstance(raw, dict):
                    raw = [{'type': t, 'weight': v.get('weight', 1), 'minCount': 1,
                            'maxCount': v.get('size', 1)} for t, v in raw.items()]
                lst = []
                for e in raw:
                    e = dict(e)
                    mn = e.pop('minCount', None); mx = e.pop('maxCount', None)
                    e.pop('size', None)
                    if mn is not None:
                        e['count'] = count_of(mn, mx)
                    lst.append(e)
                new[cat] = {'bounding_box': val.get('bounding_box', 'piece'), 'spawns': lst}
            else:
                new[cat] = val
        s['spawn_overrides'] = new
    return s

def convert_pool(obj):
    p = copy.deepcopy(obj)
    for el in p.get('elements', []):
        e = el.get('element', {})
        if e.get('projection') == 'terrain_matching':
            e['projection'] = 'rigid'
    return convert(p)

# ------------------------------------------------- terrain (noise_settings) 26.2->26.3
def convert_df(obj):
    """density function 26.2 -> 26.3: argument->input, argument1/2->left/right; plus state renames."""
    if isinstance(obj, list):
        return [convert_df(x) for x in obj]
    if isinstance(obj, dict):
        out = {k: convert_df(v) for k, v in obj.items()}
        if 'argument' in out and 'input' not in out:
            out['input'] = out.pop('argument')
        if 'argument1' in out and 'left' not in out:
            out['left'] = out.pop('argument1')
        if 'argument2' in out and 'right' not in out:
            out['right'] = out.pop('argument2')
        otype = out.get('type')
        if otype == 'minecraft:interpolated':
            if 'cell_size_xz' not in out:
                out['cell_size_xz'] = 4
            if 'cell_size_y' not in out:
                out['cell_size_y'] = 8
        if otype == 'minecraft:y_clamped_gradient':
            out['type'] = 'minecraft:gradient'
            if 'from_y' in out:
                out['from_coordinate'] = out.pop('from_y')
            if 'to_y' in out:
                out['to_coordinate'] = out.pop('to_y')
            if 'axis' not in out:
                out['axis'] = 'y'
        if otype in RENAMED_PROVIDERS:
            out['type'] = RENAMED_PROVIDERS[otype]
        return out
    if obj == 'minecraft:nether/base_3d_noise':
        return 'minecraft:overworld/base_3d_noise'  # renamed in 26.3
    return obj

def convert_spawn_target(old_entries):
    """26.2 spawn_target entries -> 26.3 (rename ranges to overworld/* ids, drop depth/humidity/offset)."""
    out = []
    for e in old_entries:
        e = dict(e)
        e.pop('depth', None); e.pop('humidity', None); e.pop('offset', None)
        mapping = {'continentalness': 'minecraft:overworld/continents',
                   'erosion': 'minecraft:overworld/erosion',
                   'weirdness': 'minecraft:overworld/ridges',
                   'temperature': 'minecraft:overworld/temperature'}
        new = {mapping.get(k, k): v for k, v in e.items()}
        out.append(new)
    return out

# ------------------------------------------------------------------- NBT I/O
class R:
    def __init__(self, buf): self.b = buf; self.i = 0
    def u(self, fmt):
        n = struct.calcsize(fmt)
        v = struct.unpack(fmt, self.b[self.i:self.i + n])[0]; self.i += n
        return v
    def s(self):
        n = self.u('>H'); v = self.b[self.i:self.i + n].decode('utf-8', 'replace'); self.i += n
        return v
    def w(self, t):
        if t == 1: return self.u('>b')
        if t == 2: return self.u('>h')
        if t == 3: return self.u('>i')
        if t == 4: return self.u('>q')
        if t == 5: return self.u('>f')
        if t == 6: return self.u('>d')
        if t == 7:
            n = self.u('>i'); v = list(self.b[self.i:self.i + n]); self.i += n; return v
        if t == 8: return self.s()
        if t == 9:
            el = self.u('>b'); n = self.u('>i')
            return (el, [self.w(el) for _ in range(n)])
        if t == 10:
            comp = {}
            while True:
                tt = self.u('>B')
                if tt == 0: return comp
                nm = self.s()
                comp[nm] = (tt, self.w(tt))
        if t == 11:
            n = self.u('>i')
            v = list(struct.unpack('>%di' % n, bytes(self.b[self.i:self.i + 4 * n]))); self.i += 4 * n; return v
        if t == 12:
            n = self.u('>i')
            v = list(struct.unpack('>%dq' % n, bytes(self.b[self.i:self.i + 8 * n]))); self.i += 8 * n; return v
        raise ValueError('tag %d' % t)

class Wr:
    def __init__(self): self.b = bytearray()
    def u(self, fmt, *v): self.b += struct.pack(fmt, *v)
    def s(self, txt):
        b = txt.encode('utf-8'); self.u('>H', len(b)); self.b += b
    def w(self, t, v):
        if t == 1: self.u('>b', v)
        elif t == 2: self.u('>h', v)
        elif t == 3: self.u('>i', v)
        elif t == 4: self.u('>q', v)
        elif t == 5: self.u('>f', v)
        elif t == 6: self.u('>d', v)
        elif t == 7:
            self.u('>i', len(v)); self.b += bytes(v)
        elif t == 8: self.s(v)
        elif t == 9:
            el, items = v
            self.u('>b', el); self.u('>i', len(items))
            for it in items: self.w(el, it)
        elif t == 10:
            for k, (tt, vv) in v.items():
                self.u('>B', tt); self.s(k); self.w(tt, vv)
            self.u('>B', 0)
        elif t == 11:
            self.u('>i', len(v)); self.b += struct.pack('>%di' % len(v), *v)
        elif t == 12:
            self.u('>i', len(v)); self.b += struct.pack('>%dq' % len(v), *v)
        else:
            raise ValueError('tag %d' % t)

def fix_block_state(comp):
    if 'Name' in comp:
        props = comp.get('Properties')
        comp['id'] = comp.pop('Name')
        comp.pop('Properties', None)
        if props:
            comp['properties'] = props

def convert_nbt_file(src, dst):
    r = R(gzip.open(src, 'rb').read())
    assert r.u('>B') == 10
    r.s()  # root name
    comp = r.w(10)
    for key in ('palette', 'palettes'):
        if key in comp and comp[key][0] == 9:
            el, items = comp[key][1]
            new = [dict_fix(it) for it in items]
            comp[key] = (9, (10, new))
    dv = comp.get('DataVersion')
    if not dv:
        comp['DataVersion'] = (3, 5023)
    w = Wr()
    w.u('>B', 10); w.s('')
    w.w(10, comp)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(gzip.compress(bytes(w.b)))

def dict_fix(it):
    st = dict(it)
    fix_block_state(st)
    return st

# ===================================================================== main
MODIFIED_STRUCTURES = ['buried_treasure', 'desert_pyramid', 'igloo', 'jungle_pyramid',
    'mansion', 'monument', 'ocean_ruin_cold', 'ocean_ruin_warm', 'pillager_outpost',
    'ruined_portal', 'ruined_portal_desert', 'ruined_portal_jungle', 'ruined_portal_mountain',
    'ruined_portal_ocean', 'ruined_portal_swamp', 'shipwreck', 'shipwreck_beached',
    'swamp_hut', 'trail_ruins', 'village_desert', 'village_plains', 'village_savanna',
    'village_snowy', 'village_taiga']

MODIFIED_POOLS = ['pillager_outpost/feature_plates',
    'village/desert/streets', 'village/desert/terminators', 'village/desert/zombie/streets',
    'village/plains/streets', 'village/plains/terminators', 'village/plains/zombie/streets',
    'village/savanna/streets', 'village/savanna/terminators', 'village/savanna/zombie/streets',
    'village/snowy/streets', 'village/snowy/terminators', 'village/snowy/zombie/streets',
    'village/taiga/streets', 'village/taiga/terminators', 'village/taiga/zombie/streets']

WHOLESALE = ['worldgen/biome', 'worldgen/noise_settings', 'worldgen/placed_feature',
             'worldgen/structure', 'worldgen/processor_list', 'worldgen/density_function',
             'dimension_type']

def strip_ns(rel):
    return rel[len('minecraft/'):] if rel.startswith('minecraft/') else rel

def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(os.path.join(OUT, 'data'))

    # 1) wholesale vanilla 26.3 copies
    for d in WHOLESALE:
        src = os.path.join(V263, 'minecraft', d)
        for root, _, files in os.walk(src):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), src)
                dst = os.path.join(OUT, 'data', 'minecraft', d, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy(os.path.join(root, f), dst)

    # 2) modified minecraft placed features from eff262
    pfdir = os.path.join(EFF, 'minecraft/worldgen/placed_feature')
    for f in sorted(os.listdir(pfdir)):
        if f == 'desktop.ini': continue
        name = os.path.splitext(f)[0]
        if name == 'trees_birch_and_oak':
            warn('dropping stale placed feature trees_birch_and_oak')
            continue
        wj(convert_placed(rj(os.path.join(pfdir, f))),
           os.path.join(OUT, 'data/minecraft/worldgen/placed_feature', name + '.json'))

    # 3) modified structures
    for name in MODIFIED_STRUCTURES:
        src = os.path.join(EFF, 'minecraft/worldgen/structure', name + '.json')
        if not os.path.isfile(src):
            warn('missing structure source: ' + name); continue
        wj(convert_structure(rj(src)),
           os.path.join(OUT, 'data/minecraft/worldgen/structure', name + '.json'))

    # 4) modified template pools
    for name in MODIFIED_POOLS:
        src = os.path.join(EFF, 'minecraft/worldgen/template_pool', name + '.json')
        wj(convert_pool(rj(src)),
           os.path.join(OUT, 'data/minecraft/worldgen/template_pool', name + '.json'))

    # 5) configured_feature -> worldgen/feature (minecraft kelp/seagrass + whole cave ns)
    for ns in ('minecraft', 'cave'):
        srcdir = os.path.join(EFF, ns, 'worldgen/configured_feature')
        if not os.path.isdir(srcdir): continue
        for f in sorted(os.listdir(srcdir)):
            if f == 'desktop.ini': continue
            name = os.path.splitext(f)[0]
            wj(conv_feat(rj(os.path.join(srcdir, f))),
               os.path.join(OUT, 'data', ns, 'worldgen/feature', name + '.json'))

    # 6) whole cave namespace: placed features, processor lists, template pools
    cfdir = os.path.join(EFF, 'cave/worldgen/placed_feature')
    for f in sorted(os.listdir(cfdir)):
        if f == 'desktop.ini': continue
        wj(convert_placed(rj(os.path.join(cfdir, f))),
           os.path.join(OUT, 'data/cave/worldgen/placed_feature', os.path.splitext(f)[0] + '.json'))
    prdir = os.path.join(EFF, 'cave/worldgen/processor_list')
    for f in sorted(os.listdir(prdir)):
        if f == 'desktop.ini': continue
        wj(convert(rj(os.path.join(prdir, f))),
           os.path.join(OUT, 'data/cave/worldgen/processor_list', os.path.splitext(f)[0] + '.json'))
    tpdir = os.path.join(EFF, 'cave/worldgen/template_pool')
    for root, _, files in os.walk(tpdir):
        for f in files:
            if f == 'desktop.ini': continue
            rel = os.path.relpath(os.path.join(root, f), tpdir)
            wj(convert_pool(rj(os.path.join(root, f))),
               os.path.join(OUT, 'data/cave/worldgen/template_pool', rel))

    # 7) biomes: modified (from eff262) overwrite the wholesale vanilla copies
    bdir = os.path.join(EFF, 'minecraft/worldgen/biome')
    for f in sorted(os.listdir(bdir)):
        if f == 'desktop.ini': continue
        name = os.path.splitext(f)[0]
        wj(convert_biome(rj(os.path.join(bdir, f)), name),
           os.path.join(OUT, 'data/minecraft/worldgen/biome', name + '.json'))

    # 8) dimension_type/overworld: vanilla 26.3 + cave deltas
    dt = rj(os.path.join(V263, 'minecraft/dimension_type/overworld.json'))
    dt['ambient_light'] = 0.2
    dt['has_ceiling'] = True
    dt['cardinal_light'] = 'nether'
    if 'attributes' in dt:
        dt['attributes'].pop('minecraft:visual/cloud_color', None)
        dt['attributes'].pop('minecraft:visual/cloud_height', None)
        dt['attributes']['minecraft:visual/ambient_light_color'] = '#1C1E28'
    wj(dt, os.path.join(OUT, 'data/minecraft/dimension_type/overworld.json'))

    # 9) timeline/day: wholesale eff262 (cave delta already applied there)
    wj(rj(os.path.join(EFF, 'minecraft/timeline/day.json')),
       os.path.join(OUT, 'data/minecraft/timeline/day.json'))

    # 9b) CAVE WORLD terrain: convert eff262 noise_settings into 26.3 external files
    for n in ('overworld', 'large_biomes', 'amplified'):
        e = rj(os.path.join(EFF, 'minecraft/worldgen/noise_settings', n + '.json'))
        # final density -> density_function/<id>/final_density.json
        fdid = 'overworld' if n == 'overworld' else ('overworld_large_biomes' if n == 'large_biomes' else 'overworld_amplified')
        wj(convert_df(e['noise_router']['final_density']),
           os.path.join(OUT, 'data/minecraft/worldgen/density_function', fdid, 'final_density.json'))
        # surface rule -> shared material rule (identical in all 3 variants)
        if n == 'overworld':
            wj(convert(e['surface_rule']),
               os.path.join(OUT, 'data/minecraft/worldgen/material_rule/overworld.json'))
        # spawn target -> patch wholesale vanilla noise_settings copy
        d = rj(os.path.join(V263, 'minecraft/worldgen/noise_settings', n + '.json'))
        d['spawn_target'] = convert_spawn_target(e['spawn_target'])
        wj(d, os.path.join(OUT, 'data/minecraft/worldgen/noise_settings', n + '.json'))

    # 10) channeling: vanilla 26.3 + can_see_sky false
    raw = open(os.path.join(V263, 'minecraft/enchantment/channeling.json')).read()
    n = raw.count('"can_see_sky": true')
    if n != 2:
        warn(f'channeling can_see_sky count={n} (expected 2)')
    dstch = os.path.join(OUT, 'data/minecraft/enchantment/channeling.json')
    os.makedirs(os.path.dirname(dstch), exist_ok=True)
    open(dstch, 'w').write(raw.replace('"can_see_sky": true', '"can_see_sky": false'))

    # 11) loot tables: zombie & zombie_villager
    z = rj(os.path.join(V263, 'minecraft/loot_table/entities/zombie.json'))
    ez = rj(os.path.join(EFF, 'minecraft/loot_table/entities/zombie.json'))
    zeal = ez['pools']
    pools = []
    for pool in z['pools']:
        entries = json.dumps(pool)
        if 'music_disc_lava_chicken' in entries:
            warn('zombie: dropped lava-chicken pool')
            continue
        for e in pool.get('entries', []):
            if e.get('name') == 'minecraft:red_mushroom':
                e['name'] = 'minecraft:leather'
                e.pop('conditions', None)
        pools.append(pool)
    z['pools'] = pools
    wj(z, os.path.join(OUT, 'data/minecraft/loot_table/entities/zombie.json'))

    zv = rj(os.path.join(V263, 'minecraft/loot_table/entities/zombie_villager.json'))
    ezv = rj(os.path.join(EFF, 'minecraft/loot_table/entities/zombie_villager.json'))
    have = json.dumps(zv['pools'])
    for pool in ezv['pools']:
        if 'minecraft:leather' in json.dumps(pool) and len(json.dumps(pool)) < 1200:
            if json.dumps(pool) not in have:
                zv['pools'].append(pool)
                warn('zombie_villager: appended leather pool')
    wj(zv, os.path.join(OUT, 'data/minecraft/loot_table/entities/zombie_villager.json'))

    # 12) cave NBT structures -> structure/ folder + field renames
    sdir = os.path.join(EFF, 'cave/structures')
    for root, _, files in os.walk(sdir):
        for f in files:
            if f == 'desktop.ini': continue
            rel = os.path.relpath(os.path.join(root, f), sdir)
            convert_nbt_file(os.path.join(root, f),
                             os.path.join(OUT, 'data/cave/structure', rel))

    print('overlay written to', OUT)

if __name__ == '__main__':
    main()
