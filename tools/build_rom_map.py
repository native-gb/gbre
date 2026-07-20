#!/usr/bin/env python3

import argparse
import csv
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path

from gbre_common import (
    Manifest,
    Range,
    Section,
    Unit,
    find_source_line,
    load_manifest,
    read_rgbds_sections,
    read_rgbds_rom_layout,
    read_rgbds_symbols,
    mapping_at,
    source_mapping_at,
)


@dataclass(frozen=True)
class EvidenceSpan:
    start: int
    end: int
    section: str
    symbol: str
    source_file: str
    source_line: int
    source_text: str
    evidence_kind: str
    confidence: str


def read_evidence_map(
    path: Path, default_kind: str = 'manual', default_confidence: str = 'unknown'
) -> list[EvidenceSpan]:
    spans = []
    with path.open(newline='') as source:
        for row in csv.DictReader(source):
            spans.append(
                EvidenceSpan(
                    start=int(row['start'], 16),
                    end=int(row['end_exclusive'], 16),
                    section=row.get('section', ''),
                    symbol=row.get('symbol', ''),
                    source_file=row.get('source_file', ''),
                    source_line=int(row['source_line']) if row.get('source_line') else 0,
                    source_text=row.get('source_text', ''),
                    evidence_kind=row.get('evidence_kind', default_kind),
                    confidence=row.get('confidence', default_confidence),
                )
            )
    return spans


def primary_symbol(names: list[str]) -> str:
    top_level = [name for name in names if '.' not in name]
    return top_level[0] if top_level else names[0]


def section_at(sections: list[Section], address: int) -> Section | None:
    for section in sections:
        if section.start <= address < section.end:
            return section
    return None


def evidence_at(spans: list[EvidenceSpan], address: int) -> EvidenceSpan | None:
    matches = [span for span in spans if span.start <= address < span.end]
    if not matches:
        return None
    return min(matches, key=lambda span: span.end - span.start)


def evidence_for_intervals(
    spans: list[EvidenceSpan], boundaries: list[int]
) -> list[EvidenceSpan | None]:
    """Select the narrowest evidence span for each boundary interval.

    Every evidence start/end is itself a boundary, so the active set cannot
    change within an interval. Sweeping those events avoids a quadratic scan
    when a content-heavy ROM contributes hundreds of thousands of spans.
    """
    starts: dict[int, list[int]] = {}
    ends: dict[int, list[int]] = {}
    for index, span in enumerate(spans):
        starts.setdefault(span.start, []).append(index)
        ends.setdefault(span.end, []).append(index)

    active: set[int] = set()
    selected = []
    for boundary in boundaries[:-1]:
        for index in ends.get(boundary, []):
            active.discard(index)
        active.update(starts.get(boundary, []))
        if active:
            best = min(
                active,
                key=lambda index: (spans[index].end - spans[index].start, index),
            )
            selected.append(spans[best])
        else:
            selected.append(None)
    return selected


def current_symbol(
    symbols: dict[int, list[str]], address: int, starts: list[int] | None = None
) -> str:
    starts = starts if starts is not None else sorted(symbols)
    index = bisect_right(starts, address) - 1
    if index < 0:
        return ''
    return primary_symbol(symbols[starts[index]])


def symbol_at(
    symbols: dict[int, list[str]], sections: list[Section], address: int,
    symbol_starts: list[int] | None = None,
) -> str:
    section = section_at(sections, address)
    if not section:
        return '<padding>'
    symbol_starts = symbol_starts if symbol_starts is not None else sorted(symbols)
    index = bisect_right(symbol_starts, address) - 1
    if index >= 0 and symbol_starts[index] >= section.start:
        return primary_symbol(symbols[symbol_starts[index]])
    return f'<section:{section.name}>'


def aggregate_status(unit: Unit | None, mapping: object | None) -> str:
    if not unit or not mapping:
        return 'unknown'
    if mapping.disposition != 'runtime':
        return 'excluded'
    if mapping.relationship != 'implements':
        if unit.understanding == 'documented':
            return 'documented'
        if unit.understanding == 'in_progress':
            return 'analyzing'
        return 'unknown'
    if unit.verification == 'verified':
        return 'verified'
    if unit.native_status == 'ported':
        return 'ported'
    if unit.native_status == 'in_progress':
        return 'implementing'
    if unit.understanding == 'documented':
        return 'documented'
    return 'unknown'


def native_locations(unit: Unit | None, manifest: Manifest) -> str:
    if not unit:
        return ''
    root = manifest.path.parent.parent
    locations = []
    for target in unit.native:
        path = (root / target.path).resolve()
        line = find_source_line(path, target.anchor) if path.exists() else None
        suffix = f':{line}' if line else ''
        locations.append(f'{target.path}{suffix}#{target.anchor}')
    return ';'.join(locations)


def make_boundaries(
    manifest: Manifest,
    sections: list[Section],
    symbols: dict[int, list[str]],
    evidence_spans: list[EvidenceSpan],
) -> list[int]:
    boundaries = {0, manifest.rom_size}
    for section in sections:
        boundaries.update((section.start, section.end))
    boundaries.update(symbols)
    for span in evidence_spans:
        boundaries.update((span.start, span.end))
    for unit in manifest.units:
        for item in unit.rom_ranges:
            boundaries.update((item.start, item.end))
    return sorted(boundaries)


def write_map(
    path: Path,
    manifest: Manifest,
    sections: list[Section],
    symbols: dict[int, list[str]],
    evidence_spans: list[EvidenceSpan],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    boundaries = make_boundaries(manifest, sections, symbols, evidence_spans)
    interval_evidence = evidence_for_intervals(evidence_spans, boundaries)
    symbol_starts = sorted(symbols)
    with path.open('w', newline='') as destination:
        writer = csv.writer(destination, lineterminator='\n')
        writer.writerow(
            [
                'start', 'end_exclusive', 'bytes', 'section', 'symbol',
                'source_file', 'source_line', 'source_text', 'unit_id',
                'relationship', 'mapping_confidence', 'claim', 'status',
                'understanding', 'native_status', 'verification',
                'disposition', 'evidence_kind', 'confidence', 'native_location', 'notes',
            ]
        )
        for index in range(len(boundaries) - 1):
            start = boundaries[index]
            end = boundaries[index + 1]
            section = section_at(sections, start)
            evidence = interval_evidence[index]
            match = mapping_at(manifest, start)
            if not match and evidence:
                match = source_mapping_at(
                    manifest, evidence.source_file, evidence.evidence_kind
                )
            unit = match[0] if match else None
            mapping = match[1] if match else None
            disposition = mapping.disposition if mapping and section else 'not_runtime'
            writer.writerow(
                [
                    f'0x{start:04X}', f'0x{end:04X}', end - start,
                    evidence.section if evidence and evidence.section else section.name if section else 'linker gap',
                    evidence.symbol if evidence and evidence.symbol else symbol_at(
                        symbols, sections, start, symbol_starts
                    ),
                    evidence.source_file if evidence else '',
                    evidence.source_line if evidence else '',
                    evidence.source_text if evidence else '',
                    unit.id if unit else '',
                    mapping.relationship if mapping else '',
                    mapping.confidence if mapping else '',
                    mapping.claim if mapping else '',
                    aggregate_status(unit, mapping) if section else 'not_runtime',
                    unit.understanding if unit else 'unknown',
                    unit.native_status if unit else 'none',
                    unit.verification if unit else 'unverified',
                    disposition,
                    evidence.evidence_kind if evidence else 'unclassified',
                    evidence.confidence if evidence else 'unknown',
                    native_locations(unit, manifest),
                    unit.notes if unit else '',
                ]
            )


def verify_map(path: Path, rom_size: int) -> tuple[int, dict[str, int]]:
    cursor = 0
    rows = 0
    statuses: dict[str, int] = {}
    with path.open(newline='') as source:
        for row in csv.DictReader(source):
            start = int(row['start'], 16)
            end = int(row['end_exclusive'], 16)
            if start != cursor or end <= start:
                raise ValueError(f"invalid coverage at ${cursor:04X}")
            byte_count = end - start
            statuses[row['status']] = statuses.get(row['status'], 0) + byte_count
            cursor = end
            rows += 1
    if cursor != rom_size:
        raise ValueError(f"coverage ends at ${cursor:04X}, expected ${rom_size:04X}")
    return rows, statuses


def main() -> int:
    parser = argparse.ArgumentParser(description='Build an auditable Game Boy ROM map')
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--rgbds-map', type=Path)
    parser.add_argument('--rgbds-sym', type=Path)
    parser.add_argument('--source-map', type=Path)
    parser.add_argument(
        '--physical-padding', action='store_true',
        help=(
            'fill RGBDS section gaps as physical linker padding and the '
            'post-link image tail as rgbfix padding'
        ),
    )
    parser.add_argument('--evidence-map', type=Path, action='append', default=[])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    if bool(args.rgbds_map) != bool(args.rgbds_sym):
        parser.error('--rgbds-map and --rgbds-sym must be supplied together')
    if args.rgbds_map:
        sections = (
            read_rgbds_rom_layout(args.rgbds_map, manifest.rom_size)
            if args.physical_padding
            else read_rgbds_sections(args.rgbds_map, manifest.rom_size)
        )
    else:
        sections = [Section(0, manifest.rom_size, 'unclassified ROM')]
    symbols = (
        read_rgbds_symbols(args.rgbds_sym, manifest.rom_size)
        if args.rgbds_sym
        else {}
    )
    evidence_spans = (
        read_evidence_map(args.source_map, 'rgbds_exact_rebuild', 'byte_exact')
        if args.source_map else []
    )
    for evidence_path in args.evidence_map:
        evidence_spans.extend(read_evidence_map(evidence_path))
    write_map(args.output, manifest, sections, symbols, evidence_spans)
    rows, statuses = verify_map(args.output, manifest.rom_size)

    summary = ', '.join(f'{status}={count}' for status, count in sorted(statuses.items()))
    print(f'Wrote {rows} exact spans covering {manifest.rom_size} bytes to {args.output}')
    print(summary)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
