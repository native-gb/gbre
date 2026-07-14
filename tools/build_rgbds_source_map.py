#!/usr/bin/env python3

import argparse
import csv
import hashlib
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from gbre_common import Section, read_rgbds_sections


ROM_SECTION_RE = re.compile(
    r'^\s*SECTION\s+"([^"]+)"\s*,\s*(ROM0|ROMX)(?:\[|\s|$)', re.IGNORECASE
)
MARKER_RE = re.compile(r'^GBRE\|([^|]+)\|(\d+)\|([^|]+)\|\$([0-9A-F]+)$')


@dataclass(frozen=True)
class Marker:
    address: int
    source_file: str
    source_line: int
    section: str
    source_text: str


@dataclass(frozen=True)
class SourceSpan:
    start: int
    end: int
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


def escaped_marker_text(value: str) -> str:
    return value.replace('\\', '/').replace('"', "'").replace('|', '/')


def marker_line(source_file: str, line_number: int, section: str) -> str:
    source = escaped_marker_text(source_file)
    section_name = escaped_marker_text(section)
    return f'PRINTLN "GBRE|{source}|{line_number}|{section_name}|", @\n'


def instrument_source(path: Path, relative_path: str) -> None:
    original_lines = path.read_text().splitlines(keepends=True)
    output = []
    current_section = ""
    in_rom = False
    macro_depth = 0

    for line_number, line in enumerate(original_lines, 1):
        code = code_without_comment(line)
        upper = code.upper()

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

        section_match = ROM_SECTION_RE.match(code)
        if section_match:
            current_section = section_match[1]
            in_rom = True
            output.append(line)
            output.append(marker_line(relative_path, line_number, current_section))
            continue

        if re.match(r'^\s*SECTION(?:\s|$)', code, re.IGNORECASE):
            current_section = ""
            in_rom = False
            output.append(line)
            continue

        if in_rom and code:
            output.append(marker_line(relative_path, line_number, current_section))
        output.append(line)

    path.write_text(''.join(output))


def copy_and_instrument(reference: Path, build_dir: Path) -> Path:
    source_dir = build_dir / "instrumented-source"
    if source_dir.exists():
        shutil.rmtree(source_dir)
    shutil.copytree(
        reference,
        source_dir,
        ignore=shutil.ignore_patterns('.git', '*.o', '*.gb', '*.map', '*.sym'),
    )
    for path in source_dir.rglob('*.asm'):
        instrument_source(path, path.relative_to(source_dir).as_posix())
    return source_dir


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(
            f"command failed ({' '.join(command)}):\n{result.stdout}{result.stderr}"
        )
    return result


def build_instrumented(
    source_dir: Path, rgbds_bin: Path, object_sources: list[str]
) -> list[str]:
    marker_output = []
    objects = []
    for source_name in object_sources:
        source = Path(source_name)
        object_name = source.with_suffix('.o').as_posix()
        result = run(
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
        marker_output.extend(result.stdout.splitlines())
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
    return marker_output


def parse_markers(lines: list[str], source_dir: Path) -> list[Marker]:
    markers = []
    for line in lines:
        match = MARKER_RE.match(line)
        if not match:
            continue
        relative_path = match[1]
        source_line = int(match[2])
        source_lines = (source_dir / relative_path).read_text().splitlines()
        original_text = source_lines[source_line - 1]
        markers.append(
            Marker(
                address=int(match[4], 16),
                source_file=relative_path,
                source_line=source_line,
                section=match[3],
                source_text=original_text.strip(),
            )
        )
    return markers


def make_spans(markers: list[Marker], sections: list[Section]) -> list[SourceSpan]:
    spans = []
    for section in sections:
        section_markers = [item for item in markers if item.section == section.name]
        by_address = {}
        for marker in section_markers:
            if section.start <= marker.address <= section.end:
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
        section_spans = [item for item in spans if item.section == section.name]
        cursor = section.start
        for span in section_spans:
            if span.start != cursor:
                raise ValueError(f"source coverage gap at ${cursor:04X} in {section.name}")
            cursor = span.end
        if cursor != section.end:
            raise ValueError(f"source coverage ends at ${cursor:04X} in {section.name}")


def write_csv(path: Path, spans: list[SourceSpan]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as destination:
        writer = csv.writer(destination)
        writer.writerow(
            [
                'start', 'end_exclusive', 'bytes', 'section',
                'source_file', 'source_line', 'source_text',
            ]
        )
        for span in spans:
            writer.writerow(
                [
                    f'0x{span.start:04X}', f'0x{span.end:04X}', span.end - span.start,
                    span.section, span.source_file, span.source_line, span.source_text,
                ]
            )


def sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Map exact RGBDS source lines to ROM bytes")
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--rgbds-bin', type=Path, required=True)
    parser.add_argument('--build-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-sha1', required=True)
    parser.add_argument('--rom-size', type=lambda value: int(value, 0), required=True)
    parser.add_argument('--source', action='append', required=True)
    args = parser.parse_args()

    source_dir = copy_and_instrument(args.reference.resolve(), args.build_dir.resolve())
    output = build_instrumented(source_dir, args.rgbds_bin.resolve(), args.source)
    rebuilt = source_dir / 'instrumented.gb'
    actual_sha1 = sha1(rebuilt)
    if actual_sha1 != args.expected_sha1.lower():
        raise ValueError(f"instrumented rebuild SHA-1 is {actual_sha1}, expected {args.expected_sha1}")

    sections = read_rgbds_sections(source_dir / 'instrumented.map', args.rom_size)
    markers = parse_markers(output, args.reference.resolve())
    spans = make_spans(markers, sections)
    verify_coverage(spans, sections)
    write_csv(args.output, spans)

    mapped = sum(item.end - item.start for item in spans)
    print(f"Instrumented rebuild matches {actual_sha1}")
    print(f"Mapped {mapped} emitted ROM bytes to {len(spans)} exact source spans")
    print(f"Wrote {args.output}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
