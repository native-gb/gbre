# Tetris deterministic oracle

This directory drives the original Tetris (JUE) v1.1 ROM in a pinned headless
mGBA build. It supports both bounded JSON Lines traces and the persistent live
`gbre.mgba.v1` service. It is verification infrastructure, not a runtime
dependency of the native game.

Build the pinned emulator once:

```sh
scripts/bootstrap-mgba-oracle.sh
```

The bootstrap checks out commit
`5157ce208a5965e8a47bf5b48b5aae5198c22a5e` and applies GBRE's maintained
headless video-buffer patch so framebuffer capture works without a window.

Record a bounded original trace:

```sh
scripts/run-tetris-oracle.sh path/to/tetris-v1.1.gb \
    oracle/inputs/start-type-a.csv build/original.jsonl 900
```

Input CSV rows are `frame,keys`. A row describes held keys until the next row;
keys may be combined with `+`. Supported names are `A`, `B`, `SELECT`, `START`,
`RIGHT`, `LEFT`, `UP`, and `DOWN`.

After building `native-gb-tetris` with its `dev` preset, run the first differential
scenario with:

```sh
scripts/compare-tetris-startup.sh path/to/tetris-v1.1.gb
```

The broader deterministic suite adds Type B level/height entry, a complete
music/level/height menu traversal with backtracking, a Type A control/audio
scenario, the complete first attract demo followed by the alternating Type B
demo, and exhaustive large-rocket and height-five Buran endings:

```sh
scripts/compare-tetris-scenarios.sh path/to/tetris-v1.1.gb
```

Compare every one of the 17 songs from a documented zeroed channel-workspace
baseline for 1,024 ticks each with:

```sh
scripts/compare-tetris-music.sh path/to/tetris-v1.1.gb
```

This checks activity, timers, durations, instruments, pitch periods, rests,
vibrato counters, and noise-register payloads on every active channel. The
native sequencer separately retains the original cross-song channel workspace
needed by instrumentless jingles.

That suite normalizes OAM pixels to native board cells and accounts for the
original's compressed initialization states while comparing shift, rotation,
soft drop, pause, preview visibility, SFX IDs, music hardware periods/timers,
and stereo routing.
The attract comparator aligns the original OAM representation with native board
coordinates and checks every gameplay frame through the recorded Type A demo,
including its final four-line clear and short return-to-title countdown.
The ending scenarios apply documented RAM patches after reaching ordinary
gameplay, then let the original ROM execute without further intervention. They
compare every state boundary, dancer frame, launch/exhaust position,
congratulations character, scoreboard phase, music selection, and return to
name entry.

The original trace includes raw state identifiers, active and preview objects,
the 10x18 board, score, lines, level, gameplay timers, input state, all three
sound-effect state blocks, music IDs, pause/pan state, Game Boy audio registers,
and PC/SP evidence. The native trace includes descriptive gameplay state and its
device-independent music/SFX director state. Comparison occurs at semantic
boundaries so native memory layout and boot overhead need not match.

The user ROM and generated traces remain untracked. mGBA source and builds live
under ignored `.cache/`; the bootstrap pins the exact upstream commit.

## Live service

Use the scenario CLI rather than invoking the socket adapter manually:

```sh
python3 tools/gbre_scenario.py live-original tetris.start-type-a \
  --frames 600 --capture --rom path/to/tetris-v1.1.gb
python3 tools/gbre_scenario.py live-landmark tetris.start-type-a gameplay \
  --rom path/to/tetris-v1.1.gb
```

`tools/mgba_service.py` verifies the ROM SHA-1 and reported pinned build before
accepting observations. It launches `oracle/tetris_service.lua` in an isolated
process and supports reset, logical pause/run, exact frame stepping, Game Boy
button masks, byte reads/writes, patches, state save/load, semantic/OAM/audio
observations, and 160×144 PNG capture. Save states have a required metadata
sidecar tying them to the scenario, ROM, emulator commit, and schema.

The service protocol is request-ID tagged and line framed. The Python owner
enforces timeouts, detects malformed or mismatched responses and child exits,
requests clean shutdown, and escalates to terminate/kill if necessary. The Lua
side holds a paused state at frame boundaries; single-step releases an exact
number of frames and freezes the resulting boundary again.

`tools/gbre_live.py` adds scenario schedules, normalized observation paths,
event-driven waits, named landmarks, comparison policies, and temporary
capture. Native-tetris starts this coordinator over private pipes. See
[`../docs/scenario-system.md`](../docs/scenario-system.md) for commands,
schemas, and troubleshooting.
