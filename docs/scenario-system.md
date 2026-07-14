# GBRE scenario system

This is the operational reference for GBRE's implemented scenario corpus and
live original/native comparison system. The design rationale, timing policy,
state-evolution rules, and bug-compatibility policy remain in
[`scenarios-comparison-and-compatibility.md`](scenarios-comparison-and-compatibility.md).

## Quick start

Build native-gb-tetris and the pinned headless mGBA once, then validate and run
the corpus:

```bash
cd /home/vega/Coding/GameDev/native-gb-tetris
cmake --build --preset dev

cd ../GBRE
./scripts/bootstrap-mgba-oracle.sh
python3 tools/gbre_scenario.py validate
python3 tools/gbre_scenario.py list --filter ending
python3 tools/gbre_scenario.py run tetris.start-type-a \
  --rom '../native-gb-tetris/roms/Tetris (JUE) (V1.1) [!].gb'
python3 tools/gbre_scenario.py run-all \
  --rom '../native-gb-tetris/roms/Tetris (JUE) (V1.1) [!].gb'
```

The old `compare-tetris-*.sh` entry points remain compatibility wrappers over
this CLI. Results now live under `GBRE/build/scenarios/<expanded-id>/`.

Inspect the live original side without opening the native app:

```bash
python3 tools/gbre_scenario.py live-landmark \
  tetris.start-type-a game-type-menu \
  --rom '../native-gb-tetris/roms/Tetris (JUE) (V1.1) [!].gb'

python3 tools/gbre_scenario.py live-original \
  tetris.type-a-controls --frames 650 --capture \
  --rom '../native-gb-tetris/roms/Tetris (JUE) (V1.1) [!].gb'
```

In native-gb-tetris, press F1 and use the separate **GBRE Scenario Comparison**
window. If it has been closed, reopen it from the main **Native Tetris RE**
window. The same catalog, coordinator, normalizer, and comparator back the UI
and CLI.

## Corpus layout

The authoritative files are readable TOML, JSON, and CSV under
`native-gb-tetris-re/scenarios/`:

```text
scenarios/
  curated/<case>/scenario.toml
  parameterized/<family>/scenario.toml
  assets/inputs/*.csv
  assets/patches/*.csv
  assets/setups/*.json
  .temporary/                 ignored disposable captures
```

SQLite and C++ binary snapshots are not authoritative. Discovery recursively
finds `scenario.toml`, validates every reference, expands parameter products,
and rejects duplicate expanded IDs. Temporary cases require explicit opt-in.

The current Tetris corpus expands to 24 cases: seven curated behaviors and 17
parameterized music cases. It covers startup into both game types, menu
traversal, gameplay controls and sound cues, the attract cycle, the large
rocket, the height-five Buran ending, and every song.

## Manifest schema version 1

```toml
schema_version = 1
id = "tetris.example"
title = "Readable title"
description = "Behavior protected by this case."
kind = "curated" # curated, parameterized, or temporary
tags = ["smoke", "gameplay"]
subsystems = ["flow", "input"]

[rom]
sha1 = "74591cc9501af93873f9a5d3eb12da12c0723bbc"

[run]
frames = 900

[original]
input = "input.csv"
input_mode = "strict" # strict or event
patches = "patches.csv" # optional
save_state = "checkpoint.ss0" # optional and pinned
adapter = "tetris"

[native]
input = "input.csv"
input_mode = "strict"
setup = "setup.json" # optional semantic recipe
adapter = "tetris"

[comparison]
profile = "fields"

[[comparison.fields]]
path = "game.score"
policy = "exact"

[[comparison.fields]]
path = "timing.drop_timer"
policy = "tolerance"
tolerance = 1

[[landmarks]]
id = "gameplay"
condition = "screen == Gameplay"
side = "both" # original, native, or both
timeout = 900
presentation = true
```

Parameterized manifests use `${name}` in IDs, titles, or descriptions and add:

```toml
[[parameters]]
name = "song_id"
values = [1, 2, 3]
```

Expansion is a Cartesian product when several parameters are present.

## Inputs and setup

Strict CSV rows are `tick,keys`. Ticks must increase. A value is held until the
next row, and keys combine with `+`:

```csv
0,NONE
540,START
541,NONE
620,RIGHT+A
```

Event-driven CSV has a header and bounded semantic waits:

```csv
action,keys,condition,timeout
wait,,screen == Gameplay,900
hold,LEFT,game.active_piece.x <= 0,120
tap,A,,2
release,LEFT,,2
```

Every wait has a positive timeout. Supported actions are `wait`, `tap`,
`hold`, and `release`. Both the live original coordinator and native frontend
consume this representation; strict mode remains the simplest reproducible
choice when exact scripted ticks are intentional.

Native setup is versioned field-based JSON. It is translated at an explicit
simulation boundary and never stores a `GameFlow` memory image:

```json
{
  "schema": "native-gb-tetris.setup.v1",
  "apply_tick": 700,
  "game": {
    "mode": "type-a",
    "level": 0,
    "height": 0,
    "score": 200000,
    "phase": "GameOver",
    "active_piece": {"type": "I", "rotation": 0, "x": 3, "y": 0}
  }
}
```

Boards contain exactly 18 ten-character rows when present. Ordinary C++
member additions do not invalidate a setup. Schema changes require an adapter
migration. A native binary checkpoint may only be an ignored rebuildable
cache.

Original save states require a `.gbre.json` sidecar containing schema,
scenario ID, exact ROM SHA-1, and pinned mGBA commit. Loading rejects any
mismatch. Be conservative about promoting them: save states may contain
copyrighted VRAM. The built-in promotion flow deliberately keeps readable
inputs/setup and drops opaque state and framebuffer artifacts.

## Observations, events, and comparison

Both sides publish `gbre.observation.v1` with `gbre.events.v1`. Stable groups
include `clock`, `screen`, `selection`, `game`, `events`, `timing`, `ending`,
`audio`, and `geometry`. Original-only PC/SP and native implementation details
are outside configured equality unless a scenario asks for them.

Comparison policies are explicit per field:

- `exact`: normalized values must be equal;
- `ordered`: ordered sequences must be equal;
- `tolerance`: numeric difference must be within `tolerance`;
- `transform`: both values pass through a named transform before equality;
- `ignore`: the field is documented but not compared;
- `intentional_difference`: a mismatch is reported as non-failing evidence and
  requires a note.

Available transforms are `identity`, `music_id_to_index`, `truthy`, and
`lower`. A missing path or unknown transform is a diagnostic, not a silent
skip. Results report the path, policy, original value, native value, and note.

## Clock and slowdown policy

Three clocks remain separate:

1. `clock.emulator_frame` is the original mGBA boundary;
2. native deterministic simulation/scenario ticks advance at 59.7275 Hz;
3. host render and wall-clock time are incidental.

High-refresh rendering never advances gameplay. Original CPU/render slowdown
is not equality by itself. Designed input windows, gravity, animation, and
music timing use exact or documented tolerant policies. When implementations
have different initialization overhead, synchronize at a named semantic
landmark rather than claiming raw frame equality.

## Live service and native UI

`tools/mgba_service.py` launches the pinned emulator as an isolated child and
speaks `gbre.mgba.v1` to `oracle/tetris_service.lua`. The service verifies ROM
and build identity and supports reset, pause, run, exact stepping, inputs,
memory reads/writes, scheduled patches, save/load, normalized observation,
landmarks, packed-RGBA live framebuffer transfer, explicit PNG evidence
capture, and clean shutdown. Requests have bounded
timeouts; EOF, invalid JSON, response-ID mismatch, and child failure are
actionable errors. Shutdown escalates from protocol request to terminate/kill.

`tools/gbre_live.py` is the scenario-aware coordinator. Native-tetris starts it
over private pipes, so the native process never links emulator code. The ImGui
frontend can:

- search ID, description, tags, and subsystems;
- load original only, native only, or both;
- reset, run, pause, and step either side or lockstep;
- advance named landmarks with timeouts;
- broadcast live keyboard/controller input;
- display pinned-mGBA and exact-size native 160x144 presentations together;
- inspect normalized comparison differences and stop on meaningful mismatch;
- capture ignored temporary state and deliberately promote readable recipes.

The emulator remains logically paused between coordinator steps. Patched
headless video-buffer and scripting hooks expose packed 160x144 RGBA frames
without PNG encoding or decoding; the native frontend reuses one streaming GPU
texture. PNG is reserved for explicit persisted evidence. Both patches are
reproducibly applied by `bootstrap-mgba-oracle.sh`.

## Authoring checklist

1. State one behavior in the description and use a stable namespaced ID.
2. Add searchable tags and actual owning subsystems.
3. Reuse an existing input/setup asset where it explains the same intent.
4. Prefer semantic setup fields over a save state or bespoke native mutation.
5. Choose the narrowest comparison fields that protect the behavior.
6. Document intentional differences instead of weakening unrelated checks.
7. Add presentation landmarks when a framebuffer/OAM review is useful.
8. Validate the entire corpus and run the new case on both sides.
9. Parameterize repetitive content coverage rather than copying manifests.
10. Keep experiments under `.temporary/`; promote only after reviewing the
    generated setup, inputs, policy, and description.

## Troubleshooting

- **ROM SHA-1 mismatch:** use Tetris JUE v1.1 with SHA-1
  `74591cc9501af93873f9a5d3eb12da12c0723bbc`.
- **Pinned mGBA missing:** run `scripts/bootstrap-mgba-oracle.sh`.
- **Coordinator closed its stream:** read the terminal error and newest
  `GBRE/build/live/*/mgba.log`; retrying the panel starts a fresh process.
- **Landmark timeout:** inspect each side's normalized observation and confirm
  the condition path/value and input schedule.
- **Immediate mismatch:** verify the field is semantic at that point. Use a
  landmark for initialization drift; do not add arbitrary frame offsets.
- **Framebuffer absent:** rebuild pinned mGBA so the maintained headless-video
  patch is present.
- **Promotion validation failure:** keep all referenced input/setup files in the
  promoted directory and rerun `gbre_scenario.py validate`.

No ROM, extracted asset cache, trace, framebuffer, temporary state, or mGBA
checkout belongs in version control.
