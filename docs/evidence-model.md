# Evidence model

GBRE treats the ROM address space as the stable center of the project. Assembly,
emulator traces, extracted assets, native code, and tests are evidence attached
to address ranges. None of those sources is required to exist.

## Four independent questions

Every byte has four useful axes:

1. **Ownership:** code, graphics, audio, text, script, table, header, padding,
   or still unclassified.
2. **Understanding:** unknown, in progress, or documented.
3. **Native status:** none, in progress, or ported.
4. **Verification:** unverified or verified against an oracle.

Keeping these axes separate avoids claims such as "ported" merely because a
range has a name or can be reassembled.

## Stable semantic units

`analysis/<game>-manifest.json` is the hand-maintained source of truth. A unit
has a stable ID, one or more ROM ranges, optional source symbols, optional
native anchors, status axes, and notes. Relationships are intentionally
many-to-many: one native function may replace several original routines, and
one original routine may become several native functions.

Native locations use an anchor string instead of a stored line number. Reports
resolve the current line each time they are generated, so ordinary source edits
do not stale the database.

Each range-to-native link states what it claims:

- `implements`: native code directly replaces some or all of the behavior;
- `derived_from`: native data was decoded from the range but does not preserve
  every source field or byte;
- `references`: useful context with no native coverage claim;
- `verified_against`: evidence used as an oracle rather than an implementation.

The link also carries `hypothesis`, `reviewed`, `exact`, or `verified`
confidence and a required plain-language claim. Mechanical source provenance
and semantic mapping confidence remain separate. Consequently, bytes marked
`derived_from` never increase direct native implementation coverage.

Ranges can also record a disposition: `runtime`, `hardware_only`,
`proven_dead`, `unused_data`, or `intentional_change`. Excluded data remains in
the gapless inventory instead of disappearing from coverage.

## Generic evidence CSV

`build_rom_map.py --evidence-map path.csv` accepts these columns:

```text
start,end_exclusive,section,symbol,source_file,source_line,source_text,evidence_kind,confidence
```

Only `start` and `end_exclusive` are required. Addresses are hexadecimal. An
emulator importer might use `evidence_kind=execution_trace`; an asset scanner
might use `tile_data`; a human annotation might use `manual`. Confidence is
descriptive rather than a numeric fiction: examples are `byte_exact`,
`observed`, `heuristic`, and `unknown`.

The generated ROM map is always gapless from byte zero through the declared ROM
size. Unknown is a valid explicit state.

## Exact RGBDS provider

For Tetris, `build_rgbds_source_map.py` copies the source tree into `build/`,
inserts `PRINTLN` probes that emit the current address without emitting ROM
bytes, and rebuilds with pinned RGBDS. The source map is rejected unless the
resulting ROM SHA-1 matches the manifest. This proves source-line ownership for
every allocated section byte without modifying the reference checkout.

Future RGBDS games can use the same provider. Other assemblers can supply their
own listing/map adapter while still producing the generic evidence columns.
