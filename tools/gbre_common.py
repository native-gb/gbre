#!/usr/bin/env python3

import csv
import json
import re
from fnmatch import fnmatchcase
from dataclasses import dataclass
from pathlib import Path


SECTION_RE = re.compile(
    r'^\s*SECTION: \$([0-9a-fA-F]{4})-\$([0-9a-fA-F]{4}) .*\["(.*)"\]$'
)
ROM_BANK_RE = re.compile(
    r'^(?:ROM[0X]\s+bank|ROM\s+Bank)\s*#(\d+)(?:\s+\(HOME\))?:$',
    re.IGNORECASE,
)
SYMBOL_RE = re.compile(r'^([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4}) (\S+)$')


def read_rom_map_rows(path: Path) -> list[dict[str, str]]:
    """Read either one ROM-map CSV or an ordered bank-shard directory."""
    if path.is_file():
        parts = [path]
    elif path.is_dir():
        parts = sorted(
            path.glob('bank-*.csv'),
            key=lambda part: int(part.stem.split('-', 1)[1], 16),
        )
        if not parts:
            raise ValueError(f'ROM-map directory has no bank shards: {path}')
    else:
        raise FileNotFoundError(f'ROM map does not exist: {path}')

    rows: list[dict[str, str]] = []
    expected_fields: list[str] | None = None
    for part in parts:
        with part.open(newline='') as source:
            reader = csv.DictReader(source)
            fields = reader.fieldnames
            if not fields:
                raise ValueError(f'ROM-map part has no CSV header: {part}')
            if expected_fields is None:
                expected_fields = fields
            elif fields != expected_fields:
                raise ValueError(f'ROM-map part has a mismatched header: {part}')
            rows.extend(reader)
    return rows


@dataclass(frozen=True)
class Range:
    start: int
    end: int
    relationship: str
    confidence: str
    claim: str
    disposition: str


@dataclass(frozen=True)
class Section:
    start: int
    end: int
    name: str
    bank: int = 0


@dataclass(frozen=True)
class NativeTarget:
    path: str
    anchor: str


@dataclass(frozen=True)
class SourceMapping:
    path: str
    evidence_kind: str | None
    relationship: str
    confidence: str
    claim: str
    disposition: str


@dataclass(frozen=True)
class Unit:
    id: str
    name: str
    rom_ranges: tuple[Range, ...]
    source_mappings: tuple[SourceMapping, ...]
    asm_symbols: tuple[str, ...]
    native: tuple[NativeTarget, ...]
    understanding: str
    native_status: str
    verification: str
    notes: str


@dataclass(frozen=True)
class Manifest:
    path: Path
    game_id: str
    title: str
    rom_size: int
    sha1: str
    addressing: str
    evidence_sources: tuple[dict, ...]
    units: tuple[Unit, ...]


RELATIONSHIPS = {'implements', 'derived_from', 'references', 'verified_against'}
MAPPING_CONFIDENCE = {'hypothesis', 'reviewed', 'exact', 'verified'}
DISPOSITIONS = {
    'runtime', 'hardware_only', 'proven_dead', 'unused_data', 'intentional_change'
}


def load_manifest(path: Path) -> Manifest:
    raw = json.loads(path.read_text())
    schema_version = raw.get("schema_version")
    if schema_version not in (1, 2):
        raise ValueError(f"unsupported manifest schema in {path}")

    game = raw["game"]
    rom_size = int(game["rom_size"])
    units = []
    ids = set()
    for raw_unit in raw.get("units", []):
        unit_id = raw_unit["id"]
        if unit_id in ids:
            raise ValueError(f"duplicate unit id: {unit_id}")
        ids.add(unit_id)

        ranges = tuple(
            Range(
                start=int(item["start"]),
                end=int(item["end"]),
                relationship=item.get("relationship", "implements"),
                confidence=item.get("confidence", "hypothesis"),
                claim=item.get("claim", ""),
                disposition=item.get("disposition", "runtime"),
            )
            for item in raw_unit.get("rom_ranges", [])
        )
        for item in ranges:
            if item.start < 0 or item.end <= item.start or item.end > rom_size:
                raise ValueError(f"invalid ROM range for {unit_id}: {item}")
            if item.relationship not in RELATIONSHIPS:
                raise ValueError(
                    f"invalid relationship for {unit_id}: {item.relationship}"
                )
            if item.confidence not in MAPPING_CONFIDENCE:
                raise ValueError(
                    f"invalid mapping confidence for {unit_id}: {item.confidence}"
                )
            if item.disposition not in DISPOSITIONS:
                raise ValueError(
                    f"invalid disposition for {unit_id}: {item.disposition}"
                )
            if schema_version >= 2 and not item.claim:
                raise ValueError(f"ROM range for {unit_id} requires a claim")

        ordered_ranges = sorted(ranges, key=lambda item: item.start)
        for previous, current in zip(ordered_ranges, ordered_ranges[1:]):
            if current.start < previous.end:
                raise ValueError(f"overlapping ROM ranges inside {unit_id}")

        source_mappings = tuple(
            SourceMapping(
                path=item["path"],
                evidence_kind=item.get("evidence_kind"),
                relationship=item.get("relationship", "implements"),
                confidence=item.get("confidence", "hypothesis"),
                claim=item.get("claim", ""),
                disposition=item.get("disposition", "runtime"),
            )
            for item in raw_unit.get("source_mappings", [])
        )
        for item in source_mappings:
            if not item.path or item.path.startswith('/') or '\\' in item.path:
                raise ValueError(
                    f"invalid source mapping path for {unit_id}: {item.path!r}"
                )
            if item.evidence_kind is not None and not item.evidence_kind:
                raise ValueError(
                    f"invalid empty evidence kind for {unit_id}:{item.path}"
                )
            if item.relationship not in RELATIONSHIPS:
                raise ValueError(
                    f"invalid source relationship for {unit_id}: "
                    f"{item.relationship}"
                )
            if item.confidence not in MAPPING_CONFIDENCE:
                raise ValueError(
                    f"invalid source confidence for {unit_id}: {item.confidence}"
                )
            if item.disposition not in DISPOSITIONS:
                raise ValueError(
                    f"invalid source disposition for {unit_id}: "
                    f"{item.disposition}"
                )
            if schema_version >= 2 and not item.claim:
                raise ValueError(
                    f"source mapping for {unit_id} requires a claim"
                )

        native = tuple(
            NativeTarget(item["path"], item["anchor"])
            for item in raw_unit.get("native", [])
        )
        units.append(
            Unit(
                id=unit_id,
                name=raw_unit.get("name", unit_id),
                rom_ranges=ranges,
                source_mappings=source_mappings,
                asm_symbols=tuple(raw_unit.get("asm_symbols", [])),
                native=native,
                understanding=raw_unit.get("understanding", "unknown"),
                native_status=raw_unit.get("native_status", "none"),
                verification=raw_unit.get("verification", "unverified"),
                notes=raw_unit.get("notes", ""),
            )
        )

    return Manifest(
        path=path.resolve(),
        game_id=game["id"],
        title=game["title"],
        rom_size=rom_size,
        sha1=game["sha1"].lower(),
        addressing=game.get("addressing", "unknown"),
        evidence_sources=tuple(raw.get("evidence_sources", [])),
        units=tuple(units),
    )


def linear_rom_address(bank: int, address: int, rom_size: int) -> int:
    if bank == 0:
        if not 0 <= address < min(rom_size, 0x8000):
            raise ValueError(f"invalid ROM0 address ${address:04X}")
        offset = address
    else:
        if not 0x4000 <= address < 0x8000:
            raise ValueError(f"invalid ROMX address {bank:02X}:${address:04X}")
        offset = bank * 0x4000 + address - 0x4000

    if offset >= rom_size:
        raise ValueError(
            f"ROM address {bank:02X}:${address:04X} exceeds {rom_size} bytes"
        )
    return offset


def read_rgbds_sections(path: Path, rom_size: int) -> list[Section]:
    sections = []
    current_rom_bank: int | None = None
    for line in path.read_text().splitlines():
        bank_match = ROM_BANK_RE.match(line)
        if bank_match:
            current_rom_bank = int(bank_match[1])
            continue
        if line and not line[0].isspace():
            current_rom_bank = None

        match = SECTION_RE.match(line)
        if not match or current_rom_bank is None:
            continue
        cpu_start = int(match[1], 16)
        cpu_end = int(match[2], 16)
        start = linear_rom_address(current_rom_bank, cpu_start, rom_size)
        end = linear_rom_address(current_rom_bank, cpu_end, rom_size) + 1
        sections.append(Section(start, end, match[3], current_rom_bank))
    sections.sort(key=lambda item: item.start)
    return sections


def read_rgbds_rom_layout(path: Path, rom_size: int) -> list[Section]:
    sections = read_rgbds_sections(path, rom_size)
    rom_banks = []
    for line in path.read_text().splitlines():
        match = ROM_BANK_RE.match(line)
        if match:
            rom_banks.append(int(match[1]))
    if not rom_banks:
        raise ValueError(f'RGBDS map contains no ROM banks: {path}')

    bank_size = 0x4000
    linked_end = min((max(rom_banks) + 1) * bank_size, rom_size)
    completed = []
    for bank_start in range(0, linked_end, bank_size):
        bank_end = min(bank_start + bank_size, linked_end)
        bank = bank_start // bank_size
        bank_sections = [
            item
            for item in sections
            if item.bank == bank and bank_start <= item.start < bank_end
        ]
        cursor = bank_start
        for section in bank_sections:
            if section.start < cursor:
                raise ValueError(
                    f'overlapping RGBDS sections at ${section.start:04X}'
                )
            if section.start > cursor:
                completed.append(Section(cursor, section.start, 'linker padding', bank))
            completed.append(section)
            cursor = section.end
        if cursor < bank_end:
            completed.append(Section(cursor, bank_end, 'linker padding', bank))

    for bank_start in range(linked_end, rom_size, bank_size):
        bank_end = min(bank_start + bank_size, rom_size)
        completed.append(
            Section(
                bank_start,
                bank_end,
                'rgbfix padding',
                bank_start // bank_size,
            )
        )

    return completed


def read_rgbds_symbol_entries(path: Path, rom_size: int) -> list[tuple[int, int, str]]:
    entries = []
    for line in path.read_text().splitlines():
        match = SYMBOL_RE.match(line)
        if not match:
            continue
        bank = int(match[1], 16)
        address = int(match[2], 16)
        try:
            offset = linear_rom_address(bank, address, rom_size)
        except ValueError:
            continue
        entries.append((bank, offset, match[3]))
    return entries


def read_rgbds_symbols(path: Path, rom_size: int) -> dict[int, list[str]]:
    symbols: dict[int, list[str]] = {}
    for _bank, offset, name in read_rgbds_symbol_entries(path, rom_size):
        symbols.setdefault(offset, []).append(name)
    return symbols


def unit_at(manifest: Manifest, address: int) -> Unit | None:
    match = mapping_at(manifest, address)
    return match[0] if match else None


def mapping_at(manifest: Manifest, address: int) -> tuple[Unit, Range] | None:
    matches = [
        (unit, item)
        for unit in manifest.units
        for item in unit.rom_ranges
        if item.start <= address < item.end
    ]
    if not matches:
        return None
    return min(matches, key=lambda match: match[1].end - match[1].start)


def source_mapping_at(
    manifest: Manifest, source_file: str, evidence_kind: str | None = None
) -> tuple[Unit, SourceMapping] | None:
    if not source_file:
        return None
    matches = [
        (unit, item)
        for unit in manifest.units
        for item in unit.source_mappings
        if fnmatchcase(source_file, item.path) and
        (
            item.evidence_kind is None or
            (evidence_kind is not None and item.evidence_kind == evidence_kind)
        )
    ]
    if not matches:
        return None
    if len(matches) > 1:
        descriptions = ', '.join(
            f'{unit.id}:{item.path}' for unit, item in matches
        )
        raise ValueError(
            f'ambiguous source mappings for {source_file}: {descriptions}'
        )
    return matches[0]


def find_source_line(path: Path, anchor: str) -> int | None:
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if anchor in line:
            return line_number
    return None
