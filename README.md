# datapacks

All my Minecraft datapack ports/creations, one folder per datapack.
Current target version: **Minecraft 26.3** (pack format 121).

| Folder | What |
|---|---|
| `cave-world-reremastered/` | Cave World Remastered v1.3.3 ported to 26.3 (26.x data copies + generator tools) |
| `revamped-floating-islands-26.3/` | Revamped Floating Islands 1.1.6 ported to 26.3 — ocean variant + true-void variant, raised 3-band island layout, beardifier structure fix, source + rebuild tool |
| `far-lands/` | Far Lands 26.3 with an editable custom range (classic hard-coded boundaries replaced by one `value`) |
| `save-the-deserts/` | Save The Deserts ported to 26.3 (+ NVS original kept for reference, needs the Lithostitched mod) |
| `xmusya-setup/` | My server setup datapack (`xmusya:setupserver`) |
| `AGENTS.md`, `Docs/` | agent memory + datapack wiki reference |

## Key 26.3 worldgen conversion notes (see AGENTS.md for the full list)

- all density-function cache wrappers removed in 26.3 (flat_cache, cache_once, cache_2d, cache_all_in_cell) — inline them
- `minecraft:shifted_noise` replaced by plain `minecraft:noise` with inline `shift_x`/`shift_z`
- `surface_rule` → `material_rule` id; aquifer fields moved into an `aquifers` object
- `minecraft:beardifier` (as a type object) must be added to custom final_density or jigsaw structures break
- `minecraft:constant` uses `"value"`, not `"argument"`; gradient `from/to_value` bounded ±1,000,000 (coordinates are not)
