# datapackgen — Minecraft datapack porting workspace

## What this project is

I (OpenCode agent) port community Minecraft datapacks to new game versions
(currently **26.3**, data/overlay pack format **121.0**, min_format 121 and
`max_format: 199` pattern, `min_format`/`max_format` **both required** — game
errors with "must declare both min_format and max_format" otherwise).

Working style so far: extract zip → inspect content → diff against vanilla
version ground truth → convert per rules → validate → ship zip to
`~/Downloads/`.

## Delivered / past work (context)

### Cave World ReRemastered (done, Nov 6)
- Fully ported "Cave World Remastered v1.3.3" to 26.3.
  Shipped as `~/Downloads/Cave World ReRemastered 26.3.zip` (~2.9 MB, 1727 files).
- GitHub: https://github.com/xmusya/cave-world-reremastered (sources + tools;
  repo renamed per user request). No releases attached (offered, user didn't answer).
- Sources at `/tmp/opencode/cave/<overlay dirs>` + generator
  `/tmp/opencode/gen263.py` + validator `/tmp/opencode/validate263.py`
  (TMP — may be wiped; regenerate knowledge from AGENTS.md rules below).
- Conversion knowledge (verified working in-game):
  - **biomes**: `spawners`→ attribute `minecraft:gameplay/natural_mob_spawns`
    (value is **FLAT** `{"spawn_costs":…, "spawns_by_category":…}` — NO
    `argument` wrapper; the jar-embedded vanilla JSON is a code-side *dump*
    that shows `{argument:…}` but datapacks must use flat);
    `creature_spawn_probability` → attribute
    `minecraft:gameplay/creature_world_gen_spawn_probability`.
    Empty spawn categories: vanilla only ships non-empty categories (safe to drop).
  - **Block states**: `{Name, Properties}` → `{id, properties}` everywhere (JSON + NBT palettes).
  - **State providers**: `minecraft:simple_state_provider` inlined as bare
    state object; others rename (`minecraft:noise_threshold_provider` →
    `noise_threshold`, etc. — see RENAMED_PROVIDERS in gen263.py).
  - **Placement**: `random_offset` → `offset` (`xz_spread` int → trapezoid
    `{"type":"minecraft:trapezoid","min":-t,"max":t,"plateau":0}`; 0 stays `0`).
  - **Features**: `configured_feature` folder → `worldgen/feature`, config
    inlined next to `type`; `random_selector` → `weighted_random_selector`
    (entries `{data:{feature,placement}, weight}`, marginal probabilities×1000).
  - **Density functions** (26.2→26.3 renames, verified):
    `argument`→`input`; `argument1`→`left`, `argument2`→`right`;
    `y_clamped_gradient`→`gradient` (`from_y`→`from_coordinate`,
    `to_y`→`to_coordinate`, add `axis:"y"`); `interpolated` now REQUIRES
    `cell_size_xz`/`cell_size_y` (vanilla uses 4/8 — good defaults);
    `minecraft:nether/base_3d_noise` renamed `minecraft:overworld/base_3d_noise`;
    `minecraft:shifted_noise` removed.
  - **noise_settings** 26.2→26.3: `surface_rule` → `material_rule` (now an ID
    referencing `worldgen/material_rule/<id>` — can override vanilla
    `minecraft:overworld` with inline converted rule tree); router slimmed to
    8 refs (`chunk_surface_level`, `continents`, `depth`, `erosion`,
    `final_density`, `ridges`, `temperature`, `vegetation` — all external
    density-function IDs); removed keys fold into: `aquifers_enabled`/ore
    veins dropped (`ore_veins_enabled` gone), aquifer fields live in new
    `aquifers` object (`barrier`, `exclusion`, `fluid_level_floodedness`,
    `fluid_level_spread`, `lava` …); `noise` drops
    `size_horizontal`/`size_vertical`; `spawn_target` entries rename keys
    (`continentalness`→`minecraft:overworld/continents`, `weirdness`→
    `minecraft:overworld/ridges`, `erosion`/`temperature` similarly prefixed;
    `depth`/`humidity`/`offset` dropped); add `debug_functions` (vanilla list).
  - **26.2→26.3 biome/worldgen folders renamed**: `configured_feature`→
    `feature`; `carver` new (configured_carver removed); `material_condition`
    /`material_rule`/`block_state_provider` new registries.
  - **Structures**: spawn_overrides modernized; village pools
    `terrain_matching`→`rigid` projection.
  - **NBT** structure templates: `structures/` → `structure/` folder; rename
    palette states; KEEP original `DataVersion` (game's own fixer upgrades).
  - **Timeline/day**: wholesale copy of effective 26.2 file worked.
  - Whole folders whose schema changed get **wholesale vanilla-26.3 copies**
    (from the misode-style data dump or jar `data/` folder) so base
    format-15 files are always shadowed by the overlay.

### Save The Deserts (done, Nov 7)
Trivial 2-recipe pack; recipe schema unchanged 26.2→26.3 but **`cookingtime`
and `experience` are REQUIRED on smelting recipes** in 26.3 ("No key
cookingtime" crash). Shipped `~/Downloads/Save The Deserts 26.3.zip` (121,
min 121, max 199). User runs it on a **Leaf 26.3 phone server** (Paperclip);
one of the packs there was a renamed copy of the same pack.

### xmusya setup datapack (done, Nov 9)
`~/Downloads/xmusya setup.zip` — function `xmusya:setupserver` replaying the
13 commands from `/home/pasha/commands.txt`. NOTE: `timber:settings/toggle/*`
are toggles (re-running flips them).

### Ground-truth data sources
- Installed 26.3 client jar with embedded vanilla datapack:
  `/home/pasha/.local/share/PrismLauncher/libraries/com/mojang/minecraft/26.3/minecraft-26.3-client.jar`
  Use `zipfile` to read `data/minecraft/...` (recipes, biomes, etc.).
- Cave World work had misode-style dumps under `/tmp/opencode/van-26.3/...`
  (MAY be wiped by tmp-cleanup — re-fetch from misode GH if needed:
  https://github.com/misode/mcmeta — branches/tag `26.3-data`, `26.2-data` etc.)
- Testing partner: Prism instance `mostly` at
  `/home/pasha/.local/share/PrismLauncher/instances/mostly/minecraft/`
  (logs in `minecraft/logs/latest.log`; packed gz `2026-11-06-N.log.gz`).
  User also tests on a remote Leaf 26.3 server (phone, `~/m/server`).

## CURRENT TASK (Nov 9): three new datapack downloads

User downloaded to `~/Downloads/` (Nov 9):
1. `Revamped_Floating_Islands_1.1.6.zip` (FI) — by Klinbee, "26.1" but declares
   formats 15–999 with overlay `overlay_1_21_9` (88–999) active at 121.
2. `No_Void_Structures_2.0.1.zip` (NVS) — by Klinbee, formats 15–999, ALL 21
   structure files use **Lithostitched** mod types
   (`lithostitched:delegating`, `lithostitched:height_filter`).
3. `Far Lands.zip` (FL) — ALREADY 26.3-native (min_format [121,0],
   max_format [121,1]).

TODO state:
- DONE Nov 9: FI ported standalone → `~/Downloads/Revamped Floating Islands
  26.3.zip` (tool `tools/port_fi.py`, build in `build/fi263`, SHIPPED to
  `Datapacks/Revamped Floating Islands 26.3.zip`). Conversion:
  overlay_1_21_9 noise_settings → 26.3 (router slimmed to 8 keys, inline
  `shifted_noise` temperature/vegetation became plain `minecraft:noise`
  with inline shift_x/shift_z — that's the 26.3 replacement; constant 2048
  `preliminary_surface_level` dropped, vanilla
  `minecraft:overworld/chunk_surface_level` used, aquifer fields moved into
  `aquifers` object keeping rfi:fluid_level_floodedness ref, spawn_target
  mapped, surface_rule → `worldgen/material_rule/overworld.json` inline
  override, defaults → bare ids). False-alarm note: referenced IDs
  overworld/{continents,erosion,ridges,offset} + end/base_3d_noise all exist
  in 26.3. **PENDING: user in-game test.** **Fixed after 26.3 test-fail Nov 9
  (log-proved): ALL cache density-function wrappers removed in 26.3 —
  flat_cache, cache_once, cache_2d, cache_all_in_cell — inline their input
  (all FI usages y-independent ⇒ lossless).** Only flat_cache errors surfaced
  for FI; watch for the others with other packs. Output path now
  `Datapacks/`.
  - **"true void" variant Nov 9 (user wants void, not oceans):**
    `Datapacks/Revamped Floating Islands 26.3 (true void).zip`. vs normal
    build: `rfi:terrain/{ocean_reduction,river_reduction,ocean_floor}` →
    `{"type":"minecraft:constant","value":0.0}`; `sea_level` = **-64**
    (vanilla floating_islands preset's anti-flooding trick). Tool has
    `VOID` flag + `VOIDED` list; rebuild normal first, then VOID=True.
  - **Structure fix Nov 9 (both variants):** FI's original final_density
    LACKS `minecraft:beardifier` which 26.3 vanilla adds for structure
    terrain adaptation (beard/burying of jigsaw structures). Without it,
    trial chambers & other jigsaws generate badly broken. Fix = wrap
    `rfi:terrain/final.json` → `add(original, "minecraft:beardifier")`
    (matches vanilla overworld/final_density layout). Awaiting test.
    **Second beardifier attempt failed: string id `minecraft:beardifier` is
    UNBOUND ("Unbound values ... [minecraft:beardifier]" — it's a df TYPE,
    not a loadable id. Use `{"type":"minecraft:beardifier"}`.)
  - **Island raise (Nov 9, user request — islands too low, y~0 structures
    should be inside islands):** `RAISE = 24` in tools/port_fi.py:
    - `depth.json`: every `minecraft:y` input → `sub(y, 24)` (range_choice,
      shifts the whole clip band up 24);
    - `terrain/base.json` + `terrain/ocean_floor.json`: all y-axis gradient
      `from/to_coordinate` += 24 (their y uses raw coordinates);
    - aquifer water levels NOT shifted (vanilla-relative, OK-ish), spawn
      target untouched. Same y→sub(y,R) trick reusable.
  - **Sparse low islands Nov 9 (user: y -64..80 shouldn't be empty):** in
    `terrain/base.json` after raise, add
    `mul(gradient(y 50+R → 90+R, 1→0), sub(end/base_3d_noise, 0.2))` —
    threshold 0.2 above vanilla's ~0.1 keeps only strong peaks below the
    main belt; fade band makes low field dissolve into the main islands.
    Tunables: right offset (0.2 = sparseness), fade band (50+R..90+R).
    **Revised to user 3-band spec:** low band y -30..60 sparse (sub 0.2,
    bottom fade -30→0 so nothing below -30), high band y 160..256 very
    sparse (sub 0.35, fades 130→160 in / 240→256 out), gap 121..159 + below
    -30 = void. `band()` helper in tools/port_fi.py handles both. user said "if you can't port+merge it with floating islands, it's fine"
  → merging FI+NVS is OFF. NVS likely loads as-is IF a 26.3 Lithostitched
  build exists (check Modrinth); otherwise user must use older game or drop it.
- User clarification (important): farlands is NOT merged with FI/NVS — **FI is
  ported standalone; FL is separate**. User uses packs one at a time.
- FI port plan (extracted copy now at `sources/fi/`):
  - effective content at 26.3 = `overlay_1_21_9/data/minecraft/worldgen/noise_settings/overworld.json`
    + root `data/rfi/worldgen/density_function/*` (10 files incl. terrain/,
    aquifer/ subfolders).
  - FI noise_settings (26.2-style) needs full 26.3 conversion per rules above;
    its router: barrier=0.11 const, temperature/vegetation = inline
    `shifted_noise` (PROBLEM: shifted_noise removed in 26.3 — vanilla 26.3
    temperature/vegetation are external files `density_function/overworld/{temperature,vegetation}.json`;
    check their content for the pattern to replicate FI's `xz_scale` 0.25 +
    shift_x/z "shift noise" behaviour, maybe 26.3 has a replacement type),
    `preliminary_surface_level` = constant 2048 (dropped in 26.3 — use
    vanilla `minecraft:overworld/chunk_surface_level`), `fluid_level_floodedness`
    = `rfi:fluid_level_floodedness`, `fluid_level_spread`/`lava` inline
    splines/noise (go into 26.3 `aquifers` object), vein_* keys dropped.
  - add fresh `aquifers` object (copy vanilla 26.3 shape, substituting rfi
    floodedness).
  - surface_rule → convert (`convert()` style state/provider renames) and ship
    as `worldgen/material_rule/overworld.json` override inside the pack
    (vanilla 26.3 noise_settings references `"minecraft:overworld"`).
  - spawn_target key mapping per rules; drop depth/humidity/offset.
  - default_block/default_fluid `{Name…}` → {id…} (verify vanilla 26.3 shape:
    possibly bare id string — vanilla 26.3 `default_fluid` looked like
    `"minecraft:water"`-style? VERIFY against jar).
  - rfi density functions: apply argument/left/right + gradient + interpolated
    cell_size fixes; verify all `minecraft:` references exist in 26.3
    (`overworld/continents`, `overworld/erosion`, `overworld/ridges`,
    `overworld/offset`, `end/base_3d_noise` — end folder exists in 26.3).
  - `noise: min_y -48, height 368` (keep), drop size_*.
  - FI also has root-format legacy noise_settings (fmt 15) —
    overlay shadows it wholesale, fine.
  - FI should REPLACE default overworld (that's how it currently works).
  - pack.mcmeta: description from FI (colored, keep), rename? keep FI name
    ("Revamped Floating Islands 26.3"), formats 121/121/199.
- FL work (DONE Nov 9): shipped
  `~/Downloads/Far Lands 26.3 (custom range).zip` (tool
  `tools/port_fl.py` — copies sources/fl and swaps the boundary functions).
  Implementation (gradient `from_coordinate` is NUMERIC-only in 26.3, so the
  range is compositional, not baked into coordinates):
  - `data/farlands/worldgen/density_function/range.json` =
    `{"type":"minecraft:constant","argument":25000.0}` ← THE only editable file
  - `farlands:coord_x` / `coord_z` = identity gradients (axis x/z,
    ±30,000,000 → ±30,000,000, clamp_to_edge, slope 1)
  - `in_farlands_x.json` replaced with
    `clamp(add(mul(2, sub(abs(farlands:coord_x), farlands:range)), -1), -1, 1)`
    (same for z with coord_z) — reproduces the original -1 inside / +1 beyond
    ramp over the same 1-block width; `in_farlands` (x+z sum) and everything
    downstream in farlands:'s density wrappers is untouched, so the pack's
    overworld/nether/end/caves/amplified/large_biomes/floating_islands wiring
    keeps working unchanged.
  - Verified (26.3, partly via error logs): `mul`/`sub` = left/right, `abs` =
    input, `add` = left/right, `clamp` = input/min/max, `constant` = **`value`**
    (NOT `argument` — log-proved Mi 26.3.x: "No key value in MapLike");
    `gradient` bounds from_value/to_value to [-1,000,000 : 1,000,000] but
    from_coordinate/to_coordinate are UNBOUNDED (original FL's 12550822
    parses). Identity coordinate gradient therefore uses ±1,000,000 values
    (clamped beyond — fine for any range ≤1M; README documents the 1M cap).
  - Ships with `README - EDITING range.txt`: MUST be installed as an
    UNZIPPED folder datapack (zip can't be edited), /reload to apply, gen
    changes only affect new chunks. **Fixed after first crash (Nov 9):**
    constant key must be `value`, coord identity gradients use ±1,000,000
    values (value-range bound).
- Original task (for reference): add **customizable farlands range, default 25000**
  (vanilla farlands ~12,550,820). Design per user choice: editable config
  FILE inside an UNZIPPED (folder) datapack — a small density-function file
  (e.g. `data/farlands/worldgen/density_function/range.json`, a
  `minecraft:constant`) referenced by the comparison functions so user edits
  ONE number. Source extracted at `sources/fl/`; the boundary logic lives in
  `data/farlands/worldgen/density_function/{in_farlands,in_farlands_x,
  in_farlands_z,corner_farlands*}.json` — locate the threshold constants
  (12550821 etc.) and replace with ref to the range constant. Document in a
  README the exact file/line to edit + that it must be run as unzipped folder
  (zip datapacks can't be edited in place).
  FL already modifies overworld/nether/end/caves/amplified/large_biomes +
  floating_islands noise settings via its own density files
  (farlands:overworld/density.json etc.) — before editing, check FL's
  structure: it likely wraps vanilla final density (REUSE whole pack, only
  change constants).

## Environment notes
- Workspace: `/home/pasha/Projects/datapackgen` (created Nov 9). User will add
  docs here later; keep AGENTS.md updated with every new finding.
- `Docs/` (user-added, Nov 9): `CreatingADatapack`, `Datapack` text docs and
  `Docs/wikis/guide/**/+page.svx` (datapack wiki: installing datapacks, cooldowns,
  performance, custom items, mob variants, debugging...) — reference these when
  writing packs, don't edit without asking.
- User language: often English, sometimes Russian. Keep answers concise.
- zsh quirk: `echo ===` fails ("== not found") — quote it: `echo "==="`.
- Use `question` TOOL for multi-choice clarifications (user likes it).
- Deliverables go to `/home/pasha/Projects/datapackgen/Datapacks/` (built/edited
  packs, with READMEs); untouched original downloads in
  `Datapacks/noeditdatapacks/` (per user's README). Some older zips still in
  `~/Downloads/` (e.g. `xmusya setup.zip`).
- ETA/user hardware: weak desktop (HD 8470D); also phone server (Leaf 26.3).
