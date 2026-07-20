#!/usr/bin/env python3

import argparse
import csv
import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from gbre_common import Section, read_rgbds_sections, read_rgbds_symbol_entries


ROM_SECTION_RE = re.compile(
    r'^\s*SECTION\s+"([^"]+)"\s*,\s*(ROM0|ROMX)(?:\[|,|\s|$)', re.IGNORECASE
)
BANK_RE = re.compile(r'\bBANK\[\$?([0-9A-F]+)\]', re.IGNORECASE)
MARKER_SYMBOL_RE = re.compile(r'(?:^|\.)GBRE_(?:ROOT_)?([0-9A-F]+)$')
INCLUDE_RE = re.compile(r'^\s*INCLUDE\s+"([^"]+)"', re.IGNORECASE)


@dataclass(frozen=True)
class MarkerDefinition:
    marker_id: int
    bank: int | None
    source_file: str
    source_line: int
    section: str
    source_text: str


@dataclass(frozen=True)
class Marker:
    address: int
    bank: int
    source_file: str
    source_line: int
    section: str
    source_text: str
    marker_id: int = 0


@dataclass(frozen=True)
class SourceSpan:
    start: int
    end: int
    bank: int
    section: str
    source_file: str
    source_line: int
    source_text: str


def code_without_comment(line: str) -> str:
    in_string = False
    escaped = False
    result = []
    for character in line:
        if character == ';' and not in_string:
            break
        result.append(character)
        if escaped:
            escaped = False
        elif character == '\\' and in_string:
            escaped = True
        elif character == '"':
            in_string = not in_string
    return ''.join(result).strip()


def marker_line(
    marker_id: int, section_root: bool = False
) -> str:
    prefix = 'GBRE_ROOT_' if section_root else '.GBRE_'
    return f'{prefix}{marker_id:08X}::\n'


def continued_line_numbers(lines: list[str]) -> set[int]:
    result = set()
    previous_continues = False
    for line_number, line in enumerate(lines, 1):
        if previous_continues:
            result.add(line_number)
        previous_continues = code_without_comment(line).endswith('\\')
    return result


def add_marker(
    output: list[str],
    definitions: dict[int, MarkerDefinition],
    marker_id: int,
    bank: int | None,
    source_file: str,
    source_line: int,
    section: str,
    source_text: str,
    section_root: bool = False,
) -> int:
    output.append(marker_line(marker_id, section_root))
    definitions[marker_id] = MarkerDefinition(
        marker_id,
        bank,
        source_file,
        source_line,
        section,
        source_text.strip(),
    )
    return marker_id + 1


def instrument_source(
    path: Path,
    relative_path: str,
    definitions: dict[int, MarkerDefinition],
    next_marker_id: int,
    forced_rom_lines: set[int] | None = None,
) -> int:
    original_lines = path.read_text().splitlines(keepends=True)
    continuation_lines = continued_line_numbers(original_lines)
    output = []
    current_section = ""
    current_bank: int | None = None
    in_rom = False
    macro_depth = 0
    repeat_depth = 0
    load_depth = 0

    for line_number, line in enumerate(original_lines, 1):
        code = code_without_comment(line)
        upper = code.upper()

        if line_number in continuation_lines:
            output.append(line)
            continue

        # LOAD blocks emit bytes into the current ROM section while assigning
        # their labels addresses in another address space (typically HRAM).
        # Symbols inserted inside the block therefore cannot identify ROM
        # offsets. Attribute the entire emitted block to its LOAD directive.
        if load_depth:
            output.append(line)
            if re.match(r'^LOAD(?:\s|$)', upper):
                load_depth += 1
            if re.match(r'^ENDL(?:\s|$)', upper):
                load_depth -= 1
            continue

        if repeat_depth:
            output.append(line)
            if re.match(r'^(?:REPT|FOR)(?:\s|$)', upper):
                repeat_depth += 1
            if re.match(r'^ENDR(?:\s|$)', upper):
                repeat_depth -= 1
            continue

        if macro_depth:
            output.append(line)
            if re.search(r'(^|\s)MACRO($|\s)', upper):
                macro_depth += 1
            if re.match(r'^ENDM(?:\s|$)', upper):
                macro_depth -= 1
            continue

        if re.search(r'(^|\s)MACRO($|\s)', upper):
            macro_depth = 1
            output.append(line)
            continue

        line_is_rom = in_rom or (
            forced_rom_lines is not None and line_number in forced_rom_lines
        )

        if line_is_rom and re.match(r'^LOAD(?:\s|$)', upper):
            next_marker_id = add_marker(
                output,
                definitions,
                next_marker_id,
                current_bank,
                relative_path,
                line_number,
                current_section,
                code,
            )
            output.append(line)
            load_depth = 1
            continue

        if line_is_rom and re.match(r'^(?:REPT|FOR)(?:\s|$)', upper):
            next_marker_id = add_marker(
                output,
                definitions,
                next_marker_id,
                current_bank,
                relative_path,
                line_number,
                current_section,
                code,
            )
            output.append(line)
            repeat_depth = 1
            continue

        section_match = ROM_SECTION_RE.match(code)
        if section_match:
            current_section = section_match[1]
            if section_match[2].upper() == 'ROM0':
                current_bank = 0
            else:
                bank_match = BANK_RE.search(code)
                current_bank = int(bank_match[1], 16) if bank_match else None
            in_rom = True
            output.append(line)
            next_marker_id = add_marker(
                output,
                definitions,
                next_marker_id,
                current_bank,
                relative_path,
                line_number,
                current_section,
                code,
                section_root=True,
            )
            continue

        if re.match(r'^\s*SECTION(?:\s|$)', code, re.IGNORECASE):
            current_section = ""
            current_bank = None
            in_rom = False
            output.append(line)
            continue

        if line_is_rom and code:
            next_marker_id = add_marker(
                output,
                definitions,
                next_marker_id,
                current_bank,
                relative_path,
                line_number,
                current_section,
                code,
            )
        output.append(line)

    path.write_text(''.join(output))
    return next_marker_id


def resolve_include(source_root: Path, parent: Path, include_name: str) -> Path:
    root_relative = source_root / include_name
    if root_relative.is_file():
        return root_relative

    parent_relative = parent.parent / include_name
    if parent_relative.is_file():
        return parent_relative

    raise ValueError(
        f'cannot resolve include {include_name!r} referenced by '
        f'{parent.relative_to(source_root)}'
    )


def trace_rom_lines(
    source_root: Path,
    path: Path,
    in_rom: bool,
    result: dict[Path, set[int]],
    stack: tuple[Path, ...],
) -> bool:
    if path in stack:
        chain = ' -> '.join(
            item.relative_to(source_root).as_posix() for item in (*stack, path)
        )
        raise ValueError(f'cyclic RGBDS include chain: {chain}')

    macro_depth = 0
    repeat_depth = 0
    lines = path.read_text().splitlines()
    continuation_lines = continued_line_numbers(lines)
    for line_number, line in enumerate(lines, 1):
        code = code_without_comment(line)
        upper = code.upper()

        if line_number in continuation_lines:
            if in_rom and code:
                result.setdefault(path, set()).add(line_number)
            continue

        if repeat_depth:
            if in_rom and code:
                result.setdefault(path, set()).add(line_number)
            if re.match(r'^REPT(?:\s|$)', upper):
                repeat_depth += 1
            if re.match(r'^ENDR(?:\s|$)', upper):
                repeat_depth -= 1
            continue

        if macro_depth:
            if re.search(r'(^|\s)MACRO($|\s)', upper):
                macro_depth += 1
            if re.match(r'^ENDM(?:\s|$)', upper):
                macro_depth -= 1
            continue

        if re.search(r'(^|\s)MACRO($|\s)', upper):
            macro_depth = 1
            continue

        section_match = ROM_SECTION_RE.match(code)
        if section_match:
            in_rom = True
        elif re.match(r'^\s*SECTION(?:\s|$)', code, re.IGNORECASE):
            in_rom = False

        if in_rom and code:
            result.setdefault(path, set()).add(line_number)

        if in_rom and re.match(r'^REPT(?:\s|$)', upper):
            repeat_depth = 1
            continue

        include_match = INCLUDE_RE.match(code)
        if not include_match:
            continue
        included = resolve_include(source_root, path, include_match[1])
        in_rom = trace_rom_lines(
            source_root,
            included,
            in_rom,
            result,
            (*stack, path),
        )

    return in_rom


def discover_rom_lines(
    source_root: Path, object_sources: list[str]
) -> dict[Path, set[int]]:
    result: dict[Path, set[int]] = {}
    for source_name in object_sources:
        source = source_root / source_name
        if not source.is_file():
            raise ValueError(f'RGBDS source root does not exist: {source_name}')
        trace_rom_lines(source_root, source, False, result, ())
    return result


def copy_and_instrument(
    reference: Path,
    build_dir: Path,
    include_roots: list[str] | None = None,
) -> tuple[Path, dict[int, MarkerDefinition]]:
    source_dir = build_dir / "instrumented-source"
    if source_dir.exists():
        shutil.rmtree(source_dir)
    shutil.copytree(
        reference,
        source_dir,
        ignore=shutil.ignore_patterns('.git', '*.o', '*.gb', '*.map', '*.sym'),
    )
    forced_lines = (
        discover_rom_lines(source_dir, include_roots) if include_roots else {}
    )
    definitions: dict[int, MarkerDefinition] = {}
    next_marker_id = 0
    source_paths = set(source_dir.rglob('*.asm'))
    source_paths.update(forced_lines)
    for path in sorted(source_paths):
        next_marker_id = instrument_source(
            path,
            path.relative_to(source_dir).as_posix(),
            definitions,
            next_marker_id,
            forced_lines.get(path),
        )
    return source_dir, definitions


def run(
    command: list[str], cwd: Path, environment: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command, cwd=cwd, env=environment, text=True, capture_output=True
    )
    if result.returncode:
        raise RuntimeError(
            f"command failed ({' '.join(command)}):\n{result.stdout}{result.stderr}"
        )
    return result


def build_direct(
    source_dir: Path, rgbds_bin: Path, object_sources: list[str]
) -> None:
    objects = []
    for source_name in object_sources:
        source = Path(source_name)
        object_name = source.with_suffix('.o').as_posix()
        run(
            [
                str(rgbds_bin / 'rgbasm'),
                '--export-all',
                '--halt-without-nop',
                '--preserve-ld',
                '--output',
                object_name,
                source_name,
            ],
            source_dir,
        )
        objects.append(object_name)

    run(
        [
            str(rgbds_bin / 'rgblink'),
            '--dmg',
            '--tiny',
            '--sym',
            'instrumented.sym',
            '--map',
            'instrumented.map',
            '--output',
            'instrumented.gb',
            *objects,
        ],
        source_dir,
    )
    run(
        [
            str(rgbds_bin / 'rgbfix'),
            '--validate',
            '--title',
            'TETRIS',
            '--old-licensee',
            '1',
            '--rom-version',
            '1',
            'instrumented.gb',
        ],
        source_dir,
    )


def build_with_make(
    source_dir: Path, rgbds_bin: Path, make_target: str
) -> None:
    environment = os.environ.copy()
    environment['PATH'] = f"{rgbds_bin}:{environment.get('PATH', '')}"
    run(['make', 'clean'], source_dir, environment)
    run(['make', make_target], source_dir, environment)


def parse_marker_symbols(
    path: Path,
    definitions: dict[int, MarkerDefinition],
    rom_size: int,
) -> list[Marker]:
    markers = []
    for bank, address, name in read_rgbds_symbol_entries(path, rom_size):
        match = MARKER_SYMBOL_RE.search(name)
        if not match:
            continue
        marker_id = int(match[1], 16)
        definition = definitions.get(marker_id)
        if not definition:
            raise ValueError(f'unknown source marker in symbol file: {name}')
        if definition.bank is not None and definition.bank != bank:
            raise ValueError(
                f'source marker {name} linked in bank {bank}, '
                f'expected {definition.bank}'
            )
        markers.append(
            Marker(
                address=address,
                bank=bank,
                source_file=definition.source_file,
                source_line=definition.source_line,
                section=definition.section,
                source_text=definition.source_text,
                marker_id=marker_id,
            )
        )
    return markers


def make_spans(markers: list[Marker], sections: list[Section]) -> list[SourceSpan]:
    spans = []
    for section in sections:
        section_markers = [
            item
            for item in markers
            if (not item.section or item.section == section.name)
            and item.bank == section.bank
        ]
        by_address = {}
        for marker in section_markers:
            if section.start <= marker.address <= section.end:
                existing = by_address.get(marker.address)
                if not existing or marker.marker_id > existing.marker_id:
                    by_address[marker.address] = marker

        addresses = sorted(by_address)
        if not addresses or addresses[0] != section.start:
            raise ValueError(f"source markers do not begin at ${section.start:04X} ({section.name})")
        if addresses[-1] < section.end:
            addresses.append(section.end)

        for index in range(len(addresses) - 1):
            start = addresses[index]
            end = min(addresses[index + 1], section.end)
            if end <= start:
                continue
            marker = by_address[start]
            spans.append(
                SourceSpan(
                    start=start,
                    end=end,
                    bank=section.bank,
                    section=section.name,
                    source_file=marker.source_file,
                    source_line=marker.source_line,
                    source_text=marker.source_text,
                )
            )
    spans.sort(key=lambda item: item.start)
    return spans


def verify_coverage(spans: list[SourceSpan], sections: list[Section]) -> None:
    for section in sections:
        section_spans = [
            item
            for item in spans
            if item.section == section.name and item.bank == section.bank
        ]
        cursor = section.start
        for span in section_spans:
            if span.start != cursor:
                raise ValueError(f"source coverage gap at ${cursor:04X} in {section.name}")
            cursor = span.end
        if cursor != section.end:
            raise ValueError(f"source coverage ends at ${cursor:04X} in {section.name}")


def write_csv(
    path: Path, spans: list[SourceSpan], omit_source_text: bool = False
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as destination:
        writer = csv.writer(destination, lineterminator='\n')
        writer.writerow(
            [
                'start', 'end_exclusive', 'bytes', 'bank', 'cpu_start',
                'cpu_end_exclusive', 'section',
                'source_file', 'source_line', 'source_text',
                'evidence_kind', 'confidence',
            ]
        )
        for span in spans:
            bank_base = span.bank * 0x4000
            cpu_base = 0 if span.bank == 0 else 0x4000
            cpu_start = cpu_base + span.start - bank_base
            cpu_end = cpu_base + span.end - bank_base
            evidence_kind = evidence_kind_for_source(span.source_text)
            writer.writerow(
                [
                    f'0x{span.start:04X}', f'0x{span.end:04X}', span.end - span.start,
                    span.bank, f'0x{cpu_start:04X}', f'0x{cpu_end:04X}',
                    span.section, span.source_file, span.source_line,
                    '' if omit_source_text else span.source_text,
                    evidence_kind, 'byte_exact',
                ]
            )


def sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def evidence_kind_for_source(source_text: str) -> str:
    code = code_without_comment(source_text)
    directive_prefix = code.split('"', 1)[0]
    directives = re.findall(
        r'(?<![A-Z0-9_])(INCBIN|DS|RB|RW|RL)(?![A-Z0-9_])',
        directive_prefix.upper(),
    )
    if 'INCBIN' in directives:
        return 'rgbds_incbin'
    if any(item in ('DS', 'RB', 'RW', 'RL') for item in directives):
        return 'rgbds_reserved'
    return 'rgbds_assembly'


def main() -> int:
    parser = argparse.ArgumentParser(description="Map exact RGBDS source lines to ROM bytes")
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--rgbds-bin', type=Path, required=True)
    parser.add_argument('--build-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-sha1', required=True)
    parser.add_argument('--rom-size', type=lambda value: int(value, 0), required=True)
    parser.add_argument('--source', action='append', default=[])
    parser.add_argument(
        '--follow-includes', action='store_true',
        help=(
            'trace --source files as textual RGBDS roots and instrument lines '
            'in nested includes reached from ROM sections'
        ),
    )
    parser.add_argument('--build-system', choices=('direct', 'make'), default='direct')
    parser.add_argument('--make-target', default='all')
    parser.add_argument('--rebuilt-rom', default='instrumented.gb')
    parser.add_argument('--map-file', default='instrumented.map')
    parser.add_argument('--sym-file', default='instrumented.sym')
    parser.add_argument('--base-rom', type=Path)
    parser.add_argument(
        '--omit-source-text', action='store_true',
        help='keep exact file/line provenance without copying source text into the CSV',
    )
    args = parser.parse_args()

    rgbds_bin = args.rgbds_bin.resolve()
    if args.follow_includes and not args.source:
        parser.error('--follow-includes requires at least one --source')

    source_dir, marker_definitions = copy_and_instrument(
        args.reference.resolve(),
        args.build_dir.resolve(),
        args.source if args.follow_includes else None,
    )
    if args.base_rom:
        shutil.copyfile(args.base_rom.resolve(), source_dir / 'baserom.gb')

    if args.build_system == 'make':
        build_with_make(source_dir, rgbds_bin, args.make_target)
    else:
        if not args.source:
            parser.error('--source is required with --build-system direct')
        build_direct(source_dir, rgbds_bin, args.source)

    rebuilt = source_dir / args.rebuilt_rom
    actual_sha1 = sha1(rebuilt)
    if actual_sha1 != args.expected_sha1.lower():
        raise ValueError(f"instrumented rebuild SHA-1 is {actual_sha1}, expected {args.expected_sha1}")

    sections = read_rgbds_sections(source_dir / args.map_file, args.rom_size)
    markers = parse_marker_symbols(
        source_dir / args.sym_file, marker_definitions, args.rom_size
    )
    spans = make_spans(markers, sections)
    verify_coverage(spans, sections)
    write_csv(args.output, spans, args.omit_source_text)

    mapped = sum(item.end - item.start for item in spans)
    print(f"Instrumented rebuild matches {actual_sha1}")
    print(f"Mapped {mapped} emitted ROM bytes to {len(spans)} exact source spans")
    print(f"Wrote {args.output}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
