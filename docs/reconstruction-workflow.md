# Reconstruction workflow

The goal is functional equivalence, not a transliteration of each LR35902
instruction. There are four separate levels of evidence:

1. **ROM coverage** identifies what owns every byte: code, tables, graphics,
   audio, header, or linker padding.
2. **Understanding** records what coherent behavior a range implements.
3. **Semantic ports** replace that behavior with direct C+-
   style C++ and record the source symbols and addresses.
4. **Differential tests** feed the same state and inputs to an emulator trace
   and the native routine, then compare the relevant outputs.

The generated ROM map is not a table of guesses. Guesses are evidence with an
explicit confidence attached to stable addresses. Unknown behavior stays
explicitly `unknown`; it is never silently treated as understood. A game with
no existing disassembly therefore begins with complete address coverage but
almost no claimed knowledge.

## Status meanings

- `unknown`: byte ownership is known, behavior is not yet interpreted.
- `documented`: behavior is understood but no native implementation exists.
- `analyzing`: the range is being understood but has no direct native coverage.
- `implementing`: a direct native implementation covers only part of the symbol.
- `ported`: the complete symbol or data range has a native counterpart.
- `verified`: the native counterpart has passed differential or exhaustive
  tests against the original behavior.
- `excluded`: understood bytes deliberately omitted because they are
  hardware-only, proven dead, unused data, or an intentional change.
- `not_runtime`: linker gaps that do not belong to an emitted ROM section.

Status is not the same as relationship. A reviewed `derived_from` range may be
well understood while contributing zero direct native implementation bytes.
The report displays relationship totals independently to keep those claims
auditable.

## Translation order

Start at the gameplay center and expand outward:

1. piece encodings, shapes, rotations, and randomizer;
2. board coordinates, collision, movement, gravity, and locking;
3. completed-row detection, collapse, score, level, and top-out;
4. Type A and Type B state machines;
5. menus, demos, high scores, endings, multiplayer, and link protocol;
6. graphics, animation timing, sound effects, and music data.

Keep original quirks visible in tests. We can intentionally fix a bug later,
but first we should know that we changed it. Each intentional divergence gets a
short compatibility note.

## Practical unit of work

For each routine or table:

1. read callers, callees, WRAM/HRAM fields, and nearby data;
2. write down inputs, outputs, persistent state, and timing assumptions;
3. translate the behavior into a small native function;
4. add focused tests, including wraparound and BCD edge cases;
5. update the semantic unit in `analysis/tetris-v1.1-manifest.json`;
6. regenerate the ROM map and only then move to the next dependency.

Later, a headless emulator oracle should snapshot state immediately before and
after selected ROM routines. That will catch the details humans miss: 8-bit
overflow, DAA/BCD behavior, input edge timing, and unusual randomizer history.
