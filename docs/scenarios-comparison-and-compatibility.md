# Scenario corpus, live comparison, and compatibility policy

## Purpose

GBRE needs a durable way to reconstruct important original-game situations,
drive the same investigation against a native port, and explain which results
must agree. Ad hoc input CSV files, emulator states, native debug mutations,
screenshots, and remembered reproduction steps do not scale to a larger game.

The scenario corpus is executable reverse-engineering evidence. It should make
a discovered behavior easy to reproduce months later without making native
runtime structs, emulator internals, or incidental frame counters part of the
public contract.

Tetris is the proving ground. GBRE owns the generic scenario schema, validator,
runner, comparison vocabulary, and emulator coordination protocol. Each native
port owns its scenario definitions, semantic state adapter, and game-specific
setup vocabulary.

## Scenario classes

Keep three different kinds of scenario instead of treating every capture as a
permanent golden test.

### Curated scenarios

Curated scenarios protect an important behavior, regression, unusual state, or
presentation landmark. They have stable IDs, descriptions, focused assertions,
and reviewed setup. There should be dozens of useful curated scenarios, not a
hand-authored file for every item in a content table.

Examples include a Tetris wall/rotation boundary, a four-line clear, a complete
menu route, a multiplayer result, and each distinct ending family.

### Parameterized coverage

Parameterized tests enumerate repeated content from extracted catalogs. One
template can cover all Tetris piece orientations or, later, every Pokemon map
warp, trainer definition, item pickup, movement permission, or script entry.
Do not commit hundreds of nearly identical scenario manifests when a generated
case has the same setup and comparison contract.

### Temporary investigations

Temporary captures are disposable emulator states, native snapshots, input
recordings, memory patches, and notes made while investigating. They may be
listed in the developer UI but are ignored by version control by default. A
useful investigation is promoted deliberately into a curated scenario with a
description and focused expectations. Most temporary captures should be
deleted without ceremony.

## Durable scenario bundle

A scenario is a small directory whose readable files are authoritative:

```text
scenarios/gameplay/type-a-first-tetris/
  scenario.toml
  setup.json
  inputs.csv
  expected.json
  original.ss0
  native-cache.bin
```

Only files needed by a particular scenario must exist.

- `scenario.toml` identifies the scenario, purpose, tags, ROM, adapters,
  comparison policy, and named landmarks.
- `setup.json` describes a semantic setup recipe or minimal overrides.
- `inputs.csv` records strict tick-indexed input when exact timing is relevant.
- `expected.json` contains focused observations and assertions.
- `original.ss0` is an optional checkpoint for the pinned emulator.
- `native-cache.bin` is always a disposable optimization, never evidence.

An original emulator state may be committed when the project is able to
distribute it and the state is tied to an exact ROM hash, emulator build,
state-format version, initial frame, and manifest. Emulator states are useful
for expensive-to-reach situations. They must not be the only explanation of
what a scenario means.

Be conservative about publishing save states: an emulator state can contain
ROM-derived data. Private project policy and public distribution policy may
therefore differ.

## Native setup and state evolution

Never persist raw C++ object memory. Padding, pointers, container layout, and
ordinary struct changes make such snapshots unsafe and needlessly brittle.

The durable native starting point is a field-based semantic recipe:

```json
{
  "mode": "type-a",
  "level": 9,
  "board": [
    "..........",
    "####.#####"
  ],
  "active_piece": {
    "type": "I",
    "rotation": 1,
    "x": 4,
    "y": 15
  },
  "next_piece": "T"
}
```

A game-specific adapter translates this stable vocabulary into current runtime
state. Adding an internal field should normally change the adapter once rather
than invalidate every scenario. New nonessential fields receive explicit
defaults. A semantic schema change increments the schema version and supplies a
small migration when preserving older scenarios is worthwhile.

Some large games will eventually need complete native checkpoints because a
semantic recipe would be enormous. Those checkpoints still use an explicit,
field-based, versioned serialization separate from runtime structs. They can be
loaded and resaved by migrations. Generated binary caches may accelerate this
path but remain rebuildable.

Prefer composition over copied state:

```toml
base = "pokemon-red/standard-adventure"
location = "celadon-gym.before-erika"
party = "fixtures/level-30-party"
trigger = "scripts/celadon-gym/erika"
```

## Input forms

Support two complementary input descriptions.

Strict input is indexed by original frame or native simulation tick and is
appropriate when DAS, gravity, lock, music, or another cadence is itself under
test:

```text
40,RIGHT+A
42,RIGHT
45,NONE
```

Event-driven input waits for semantic conditions and is more resilient when
two implementations take different time to reach the next screen:

```text
wait screen == GameTypeMenu
tap RIGHT
tap START
wait phase == Falling
hold LEFT until active_piece.x == 0
```

Every wait has a timeout and reports the last normalized observation on
failure. Live controller input can be broadcast to both implementations and
recorded as a temporary investigation. Promotion chooses whether the final
scenario keeps strict timing, semantic actions, or both.

## Stable observations, not native structs

Original and native adapters publish the same small normalized observation
schema. Comparison code never reads native runtime structs directly and does
not require the native memory layout to resemble WRAM.

```json
{
  "screen": "gameplay",
  "phase": "falling",
  "active_piece": {"type": "T", "rotation": 1, "x": 4, "y": 8},
  "preview": "I",
  "score": 1200,
  "level": 2,
  "lines": 13,
  "events": ["piece-moved"]
}
```

Adapters may also expose diagnostic raw state such as PC, SP, WRAM bytes, and
native-only counters. Diagnostic fields help explain a mismatch but are not
part of semantic equality unless a scenario opts into them.

## Comparison contracts

Literal whole-state equality on every displayed frame is not the default. Each
scenario selects the relationship appropriate to the behavior:

| Evidence | Normal comparison |
| --- | --- |
| Board, score, level, piece, menu selection | Exact at synchronization landmarks |
| Gameplay and presentation events | Same order and semantic payload |
| Designed gravity, DAS, lock, and animation cadence | Exact logical ticks or an explicit tolerance |
| Screen transitions | Same sequence; timing policy selected per transition |
| Incidental Game Boy CPU stalls | Ignored or declared native difference |
| Host rendering and wall time | Never part of simulation equality |
| PC/SP, stack, DIV, temporary WRAM | Diagnostic unless explicitly selected |
| Audio driver activity | Event/register comparison |
| Audio output | Separate PCM likeness comparison |
| Presentation | Geometry or framebuffer comparison at named landmarks |

Supported field policies should remain small and explicit:

- `exact` requires equal normalized values;
- `ordered` requires the same event or transition sequence;
- `tolerance` permits a documented numeric or tick window;
- `transform` compares after a named adapter-owned conversion;
- `ignore` excludes incidental state;
- `intentional_difference` records a reviewed native behavior.

## Timing domains

Keep three clocks separate:

1. original emulator frames or hardware ticks;
2. native deterministic simulation ticks;
3. host render and wall-clock time.

High-refresh rendering must not accelerate gameplay and is not a comparison
clock. The live coordinator may step each implementation until the next named
landmark instead of assuming that original frame 500 always corresponds to
native tick 500.

Preserve designed timings that affect play unless the port records an
intentional change. Incidental slowdown caused by original CPU workload,
rendering limits, or hardware stalls does not need to be reproduced. If an
original stall changes meaningful input or game-rule behavior, investigate it
and choose an explicit compatibility policy rather than allowing accidental
drift.

## Live coordinator and ImGui

The batch runner remains the reproducible CI interface. A live coordinator
adds a small command protocol shared by the pinned emulator adapter and the
native port:

```text
load scenario-id
reset original
reset native
input both RIGHT+A
step original 1
step native 1
advance both next-landmark
observe both gameplay
capture both framebuffer
```

GBRE should own the coordinator and emulator service. A native port may expose
its adapter in-process. The native ImGui client can then provide:

- scenario search by ID, description, tag, and subsystem;
- load, reset, run, pause, and independent stepping;
- broadcast controller input;
- run both sides to the next shared landmark;
- original framebuffer beside native presentation;
- normalized state, event, timing, geometry, and audio differences;
- automatic pause on a meaningful mismatch;
- temporary recording and deliberate promotion to a curated scenario.

The UI is a frontend to the same schema and comparison engine used by the CLI;
it must not grow a second set of scenario semantics.

## Avoiding a maintenance bomb

Scenario count is not the main risk. Bespoke setup logic and indiscriminate
golden state are the risks.

- Curate behaviors and regressions; generate repetitive content coverage.
- Describe intent and minimal overrides rather than complete state by default.
- Reuse bases, parties, inventories, maps, boards, and battle setups.
- Keep assertions narrow enough to explain the protected behavior.
- Put all runtime-state translation in one adapter per game.
- Validate every manifest and reference before a scenario enters CI.
- Keep scenarios independent rather than chaining their output as hidden setup.
- Run a small smoke tier per build, a broader scheduled tier, and exhaustive
  parameterized coverage on demand.
- Delete curated scenarios whose protected behavior is no longer meaningful.
- Treat opaque native snapshots as caches, not the source of truth.

A schema migration that touches many readable files is acceptable when game
semantics genuinely change. Adding an unrelated runtime member is not.

## Bug and compatibility policy

A native port preserves the original game's meaningful content and mechanics;
it does not reproduce the original machine merely to preserve every accident.
Understand a quirk before changing it, then assign one reviewed disposition:

- `fixed_default`: corrected native behavior with no compatibility option;
- `fixed_with_toggle`: corrected by default, with a narrowly scoped legacy
  option because the quirk has real player, historical, or research value;
- `preserved_quirk`: retained because it materially defines expected gameplay;
- `hardware_only_omitted`: tied to timing, memory, rendering, or hardware that
  the native architecture replaces;
- `undecided`: understood evidence exists but policy still needs review.

Fix broken behavior by default. Compatibility toggles are optional and rare;
do not build a general glitch framework in anticipation of possible interest.
Each toggle needs a concrete use case and focused tests for both settings.

Use 8-bit arithmetic where gameplay or data-format semantics require it, not
as a universal implementation style. Fixed WRAM addresses become named native
state, banked pointers become validated IDs or references, and renderer/audio
hardware becomes native subsystems.

Memory corruption, arbitrary execution, pointer alias accidents, and exact
stack or WRAM exploits are normally `hardware_only_omitted`. Preserving Pokemon
arbitrary-code execution, for example, would require memory-layout constraints
that turn the port back toward an emulator. An iconic glitch may instead be
recreated intentionally as a safe optional feature without preserving the
corruption mechanism.

ROM accounting still covers omitted behavior. Every range states whether it
became native logic, extracted data, a hardware replacement, proven dead code,
or an intentional compatibility change. Accounting for every byte never means
transliterating every instruction or exposing original memory unsafely.

## Implemented Tetris proof

The first consumer now implements schema version 1, validation/discovery,
strict and event inputs, comparison policies, normalized observations/events,
semantic native setup, a persistent pinned-mGBA service, CLI and ImGui clients,
temporary capture/promotion, and the complete 24-case expanded corpus. Existing
CSV/JSONL tools remain compatibility adapters. Operational commands and the
schema reference are in [`scenario-system.md`](scenario-system.md).

The readable corpus remains authoritative. A searchable SQLite index may be
generated later when corpus size makes it useful, but is not required for the
current scale.
