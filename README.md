# GBRE

GBRE is a research and interoperability toolkit for analyzing user-supplied
Game Boy software and developing native reimplementations.

It provides a ROM-range data model, source-map generation, HTML coverage maps,
VS Code navigation, deterministic emulator control, semantic scenarios, and
original/native comparison infrastructure. A complete disassembly is useful
when one exists but is not required: a new manifest can begin as one unknown
ROM-sized range and accumulate evidence from manual analysis, traces, asset
detectors, and partial disassemblies.

GBRE is deliberately a separate repository from every game port and every
game-specific research database.

## Repository boundary

```text
GBRE/                              generic tools, schemas, editor support
native-gb-<game>/                  public native C++ port
native-gb-<game>-re/               private game map, scenarios, oracle glue
```

The public port is the only active C++ workspace. A `-re` repository contains
annotations and reproducible evidence; it must not become a fork of the port.
GBRE contains the reusable machinery. Some early Tetris-specific adapters remain
here while the adapter API is generalized, but the Tetris manifest and scenario
database do not.

## Core tools

- `tools/build_rom_map.py` builds a gapless byte inventory from a semantic
  manifest and any available evidence maps.
- `tools/shard_rom_map.py` splits a large gapless CSV at fixed ROM-bank
  boundaries without changing its schema or coverage.
- `tools/build_rgbds_source_map.py` maps emitted RGBDS source lines to exact ROM
  ranges while verifying that instrumentation does not change the rebuilt ROM.
- `tools/build_report.py` produces the local interactive ROM heatmap.
- `tools/gbre.py` performs command-line lookups by address, unit, or source.
- `tools/gbre_scenario.py` validates and runs external scenario databases.
- `tools/gbre_live.py` provides the line-oriented coordinator used by native
  development UIs.
- `editor/vscode-gbre` adds CodeLens and jump navigation between native code,
  reference source, and ROM ranges.

## Run tests

```bash
./scripts/test.sh
```

The generic test suite runs without a ROM. Tetris integration checks become
available when `../native-gb-tetris-re` and the ignored local inputs exist.

## Install editor navigation

```bash
./scripts/install-vscode-navigation.sh
```

Each native workspace configures four paths: its manifest, ROM map, reference
root, and HTML report. Those paths normally point into the corresponding private
`-re` sibling. ROM-map readers accept either one CSV or a directory of
hexadecimal `bank-*.csv` shards. `F12` or Ctrl-click follows a
`GBRE: game.unit` marker; dedicated commands jump to assembly, native code, or
the heatmap.

## Starting a game without a disassembly

Create a manifest containing the ROM size, accepted hashes, and an initial
unknown unit. Running `build_rom_map.py` with only that manifest already yields
a complete inventory. Refine it with evidence-span CSV files from:

- cartridge header and pointer-table analysis;
- emulator execution and memory-access traces;
- tile, text, audio, compression, map, and script detectors;
- manual annotations or a later partial/rebuildable disassembly.

Evidence and implementation are separate claims. A native function may
`implement`, be `derived_from`, `reference`, or be `verified_against` a source
range. A dense modern implementation does not need to mirror the original
memory layout.

## Data and distribution

GBRE contains no ROM and no game-specific scenario database. Fetched emulator
and reference repositories, builds, reports, traces, captures, and local inputs
are ignored. See [Repository and legal model](docs/repository-and-legal-model.md)
and [Public release checklist](docs/public-release-checklist.md).

## License

The original source code in this repository is available under GPL-3.0-only.
Third-party components and fetched references retain their own licenses.
