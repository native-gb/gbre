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
has a stable ID, explicit ROM ranges and/or exact-rebuild source mappings,
optional source symbols, optional native anchors, status axes, and notes.
Relationships are intentionally
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

For content-heavy RGBDS projects, a unit may use `source_mappings` with an
exact relative path or shell-style path pattern. A source mapping carries the
same relationship, confidence, claim, and disposition as a ROM range. It is
applied only to byte-exact source-map spans whose `source_file` matches, so a
family such as `data/maps/objects/*.asm` can remain auditable without copying
hundreds of scattered generated offsets into the manifest. Explicit ROM ranges
take precedence, and ambiguous source patterns are rejected rather than picked
arbitrarily. Without an exact source map, source mappings make no coverage
claim. An optional `evidence_kind` further limits a mapping to spans such as
`rgbds_incbin`; this permits a mixed assembly file's binary payloads to advance
without making a claim about its adjacent executable code.

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

`build_rgbds_source_map.py` copies the source tree into an ignored build
directory, inserts zero-byte exported marker labels, resolves those labels from
the linker symbol file, and rebuilds with pinned RGBDS. Marker labels work with
legacy RGBDS 0.3.5 as well as newer releases and preserve ROM0/ROMX bank
identity. The source map is rejected unless the resulting ROM SHA-1 matches the
expected image. This proves source-line ownership for every allocated section
byte without modifying the reference checkout.

The provider labels `INCBIN` spans separately from authored assembly/data and
reserved directives. Linker gaps remain explicit `not_runtime` ranges. None of
those mechanical classifications changes a semantic unit's understanding or
native verification status.

Future RGBDS games can use the same provider. Other assemblers can supply their
own listing/map adapter while still producing the generic evidence columns.
