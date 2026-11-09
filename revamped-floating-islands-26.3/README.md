# Revamped Floating Islands 26.3

Port of Revamped Floating Islands 1.1.6 (Klinbee) to Minecraft 26.3.

Install as a normal zip datapack. Two variants:

- `Revamped Floating Islands 26.3.zip` — original behavior (oceans = void fill)
- `Revamped Floating Islands 26.3 (true void).zip` — true void: ocean/river
  sinking + sunken ocean floor removed, sea_level -64 (no void flooding)

## Island layout (customized, 3 bands)

- main island belt, tops ~ y 80..120 (raised +80)
- sparse small islands y -30..60 ("small", catch-yourself-on-the-void field)
- very sparse AND small peaks y 160..256
- y < -30 and the 121..159 gap stay void
- trial chambers & other jigsaw structures generate correctly — added
  `{"type":"minecraft:beardifier"}` into final_density (missing in the
  26.1 original; required by 26.3 structure terrain adaptation)

## Rebuild

`python3 port_fi.py` — reads `src/originals`, writes the zips. Flags:
`VOID` (true-void), `RAISE` (island lift). The 3-band layout lives in the
3-band block in the tool; each band = fade-in/fade-out + noise threshold +
gain (gain < 1 makes islands smaller).

26.3 conversion facts are in the root `AGENTS.md`.
