# Far Lands 26.3 (custom range)

26.3-native Far Lands datapack, modified so the Far Lands boundary is
user-editable: the hard-coded ±12,550,822 gradients were replaced by
`farlands:coord_x/coord_z` identity gradients + arithmetic against
`farlands:range` (a single `minecraft:constant`).

## Install (MUST be unzipped!)

1. Download and UNZIP `Far Lands 26.3 (custom range).zip`
2. Put the folder (the one containing `pack.mcmeta`) into the world's
   `datapacks/` folder
3. Run `/reload`

## Change the range

Edit `data/farlands/worldgen/density_function/range.json`:

```json
{"type": "minecraft:constant", "value": 25000.0}
```

- default 25 000 blocks; vanilla Far Lands are ~12 550 821 out
- max supported: 1 000 000 (26.3 caps gradient values there)
- `/reload` to apply; only newly generated chunks change

Rebuild from originals: `python3 port_fl.py` (see src/originals/fl).
