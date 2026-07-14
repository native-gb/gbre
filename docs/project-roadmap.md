# Native Game Boy reconstruction roadmap

This document preserves the project-level direction shared by GBRE and every
native game repository. Individual ports own their implementation plans; GBRE
owns the reusable reverse-engineering evidence model and tools.

## Objective

Reconstruct Game Boy games as readable native C++ programs rather than ship an
emulator wrapped in a new frontend. Preserve the complete intended game,
content, rules, scripts, audio, and observable behavior. Hardware accidents,
memory-layout exploits, and unwanted bugs may be fixed or made optional.

The player supplies an exact supported ROM. The native program validates it and
extracts copyrighted assets into memory at runtime. ROMs, extracted assets,
emulator states, and frame captures remain untracked.

Native ports should make later enhancements possible without contaminating the
original reconstruction:

- high-refresh rendering and low-latency input;
- native-resolution, widescreen, ultrawide, and 4K presentation;
- larger cameras and world views where the original hardware window was the
  limiting factor;
- optional modern pacing, rules, accessibility, and effects;
- developer tools that inspect semantic native state instead of packed Game Boy
  RAM.

## Repository topology

### `GBRE`

Shared analysis and evidence tooling. It owns:

- complete ROM-byte inventories and evidence/status maps;
- assembly/disassembly/native/ROM navigation;
- reproducible extraction and report generation;
- the pinned mGBA oracle service;
- readable scenario schemas, runners, observations, and comparison policies;
- workflows for games with and without rebuildable disassemblies.

GBRE is not a containing repository and is not a player-facing runtime
dependency.

### `native-gb-tetris`

The first complete proving ground. It owns the Tetris simulation, flow,
presentation, input, audio, tests, and optional enhancements. It proves the
byte-accounting, runtime-extraction, native-audio, scenario, and emulator-oracle
workflow before those ideas are generalized.

### `native-gb-super-mario-land`

The second port, targeting **Super Mario Land (World) (Rev A)**. This is the
first scrolling action game and should reveal which Tetris systems are truly
reusable. It will remain a sibling repository, not a child of GBRE or Tetris.

Supported ROM identity:

- filename convention: `Super Mario Land (World) (Rev A).gb`;
- size: 65,536 bytes;
- SHA-1: `418203621b887caa090215d97e3f509b79affd3e`;
- revision: 1.

The exact rebuildable disassembly and toolchain revision must be pinned and
verified against this digest before it becomes address evidence.

### Later ports

Each later game receives another sibling `native-*` repository. Candidate work
can progress from small action games to Zelda and Pokemon-scale games. Do not
extract a shared runtime merely because two files look similar; wait until a
second port demonstrates the actual common boundary.

## Shared versus game-owned code

Keep these shared in GBRE:

- ROM identity and byte-range evidence formats;
- report and navigation tools;
- disassembly source-map construction;
- scenario corpus infrastructure and emulator control;
- generic extraction provenance and lossless round-trip concepts.

Keep these local until repeated use proves otherwise:

- game state and rules;
- screen/level flow;
- asset decoders whose format is game-specific;
- rendering layout and effects;
- native save/state adapters;
- audio-driver interpretation.

Gubsy can supply SDL3 windowing, render targets, controller bindings, menus,
ImGui, persistence, and display settings. A port should import the useful
pieces without making its headless game logic depend on Gubsy or SDL.

A register-driven Game Boy audio library is a likely shared project, but Tetris
should first finish its APU likeness pass and SML should exercise the proposed
API. Extract the library only after both games reveal the stable boundary.

## Standard reconstruction sequence

### 1. Identify the target

- record hashes, size, cartridge header, mapper, region, and revision;
- choose one canonical ROM revision;
- keep the ROM ignored from the first commit;
- pin and byte-verify any reference disassembly.

### 2. Account for the ROM

- create a manifest and an all-unknown byte inventory;
- map header, code, data, gaps, banks, and known assets;
- attach evidence without pretending guesses are verified;
- keep every byte classified through completion.

### 3. Build a headless semantic core

- translate behavior into direct C+-style C++ state and functions;
- use descriptive state instead of preserving packed/reused RAM;
- make inputs and random samples explicit;
- test rules without SDL, rendering, audio devices, or ImGui.

### 4. Extract content at runtime

- validate the supplied ROM before selecting a decoder profile;
- decode graphics, maps, actors, scripts, text, music, and effects in memory;
- record source ranges and decoder versions;
- add lossless or semantic round-trip checks where possible.

### 5. Rebuild native presentation

- reproduce original layouts and timing well enough to verify behavior;
- use native windowing, controller input, high-refresh rendering, and audio;
- retain separate world, camera, anchored-UI, Game Boy screen, and host-pixel
  coordinate systems;
- make mGBA an optional development oracle, never a shipped runtime dependency.

### 6. Verify with scenarios

- prefer readable setup plus input recipes over opaque save-state collections;
- compare semantic landmarks instead of assuming emulator, simulation, and
  renderer clocks are identical;
- use exact frame/state comparison only where the contract requires it;
- retain small curated regression cases and generate broad parameterized cases.

### 7. Add native enhancements

- keep an Original preset for evidence and comparison;
- separate presentation, pacing, and rule changes;
- store the enhancement profile in replays and high-score identities;
- provide accessibility overrides for motion, flashing, contrast, and audio.

## Super Mario Land goals

SML should be a deliberate step up from Tetris, not a throwaway second demo.
The port needs:

- complete overworld, underground, water, and shooter-stage behavior;
- Mario movement, collision, scrolling, enemies, projectiles, blocks, items,
  bosses, checkpoints, deaths, scoring, timers, lives, and continues;
- all levels, level scripts, object streams, tilemaps, animations, music, and
  sound effects extracted from the supported ROM;
- deterministic headless input/random/state control;
- controller play and high-refresh rendering;
- original 160x144 presentation for evidence;
- optional native-resolution widescreen camera and expanded backgrounds that
  do not activate off-camera objects incorrectly;
- scenario cases for movement, jumps, collisions, pipes, autoscroll, bosses,
  death/restart, and full-level completion.

The first SML milestone is not “Mario appears in an SDL window.” It is a pinned
ROM/disassembly pair, a complete initial byte inventory, a headless cartridge
header/profile test, and one mapped vertical slice from input through native
state and ROM-derived presentation.

## Pokemon-scale destination

The long-term harness should support loading a complete world, actors, and
triggers into native semantic state, then rendering it with arbitrary camera
and zoom controls. That does not mean simulating every actor continuously.
World state, activation policy, scripts, and rendering visibility must remain
separate so an expanded view does not change game behavior accidentally.

For Pokemon this implies:

- all maps and connections decoded into world coordinates;
- persistent actors and script triggers represented independently of the
  original banked-memory window;
- explicit activation and update policies;
- zoomable whole-world inspection as a developer or enhancement mode;
- compatibility toggles only for bugs worth preserving, never an attempt to
  reproduce arbitrary-code-execution memory layouts in native C++.

## Immediate work order

1. Keep Native Tetris stable, fix discovered regressions, and add its small
   enhancement system without weakening Original mode.
2. Create `native-gb-super-mario-land`, place the verified Rev A ROM under an ignored `roms/`
   path, and copy the shared C+- `AGENTS.md`.
3. Pin and byte-verify the SML disassembly/toolchain.
4. Add the SML manifest, unknown ROM map, source map, and GBRE report.
5. Inventory SML banks, engine loops, level/object data, graphics, and audio.
6. Begin the headless movement/collision/level-stream reconstruction and its
   first emulator scenarios.

This roadmap is intentionally durable and cross-repository. Game-specific
task lists should link here rather than duplicate the larger goal incompletely.
