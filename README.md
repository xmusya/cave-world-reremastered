# Cave World ReRemastered (26.3 port)

Brings back the classic **Cave** world type — the entire Overworld becomes a vast
cave system — as a Minecraft data pack.

- Original pack: [Cave World Remastered; on Modrinth](https://modrinth.com/datapack/cave-world-reremastered/versions) (v1.3.3 covers up to MC 26.2)
- This repository: same pack ported to **Minecraft 26.3** (data/overlay format `121.0`)

## Built data pack

See the repo release, or build it yourself by zipping the repository root:

```
zip -r "Cave World Re&amp; 26.3.zip" . -x '*desktop.ini' -x tools_scripts/\* -x pack.png -x '*.git*'
```

(Drop `pack.png` in the zip root too if you want it shown in the pack selection UI.)

## How the port works

Minecraft 26.3 changed a lot of worldgen JSON, so the pack keeps working via
overlay versions:

| overlay directory | covers |
|---|---|
| (root `data/`) | data format 15 (1.20.3 base) |
| `1.20.5-1.20.6` … `26.2` | newer game versions (from the original pack) |
| `26.3` | full conversion to 26.3 (this port) |

Notable 26.3 conversions applied in the `26.3` overlay:

- vanilla-26.3 wholesale copies for `worldgen/biome`, `noise_settings`,
  `placed_feature`, `structure`, `processor_list`, `density_function` and
  `dimension_type` so no legacy-format root file can be parsed
- pack-modified biomes: `spawners`/`spawn_costs` → the
  `minecraft:gameplay/natural_mob_spawns` attribute (flat value), and
  `creature_spawn_probability` → `minecraft:gameplay/creature_world_gen_spawn_probability`
- the cave-terrain formula (`final_density`), surface rule (`material_rule/overworld.json`)
  and spawn targets converted out of the 26.2 noise settings, including renames
  (`argument`→`input`, `argument1/2`→`left/right`, `y_clamped_gradient`→`gradient`
  with `from_coordinate`/`to_coordinate`, mandatory `interpolated` cell sizes,
  `minecraft:nether/base_3d_noise` → `minecraft:overworld/base_3d_noise`)
- `configured_feature` → `worldgen/feature` (configs inlined; old
  `random_selector` re-expressed as `weighted_random_selector`)
- `random_offset` → `offset` placement modifiers; `{Name, Properties}` block
  states → `{id, properties}` everywhere (JSON and NBT)
- village pools `terrain_matching` → `rigid`; structure spawn overrides modernized
- the 112 `.nbt` structure templates renamed palette states and kept their
  original `DataVersion` so the game's own fixer upgrades them

`gen263.py` regenerates the whole `26.3/` overlay from the effective 26.2 pack
content; `validate263.py` sanity-checks the result. They are development tools,
not required to use the pack.

## Credits

- Big thanks to the original pack author — see the
  [Modrinth versions page](https://modrinth.com/datapack/cave-world-reremastered/versions).
