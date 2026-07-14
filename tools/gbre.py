#!/usr/bin/env python3

import argparse
import csv
import re
import subprocess
from pathlib import Path

from gbre_common import load_manifest


def read_rows(path: Path) -> list[dict]:
    with path.open(newline='') as source:
        return list(csv.DictReader(source))


def query_address(query: str) -> int | None:
    match = re.fullmatch(r'(?:0x|\$)?([0-9a-fA-F]+)', query.strip())
    return int(match[1], 16) if match else None


def find_row(rows: list[dict], query: str) -> dict:
    address = query_address(query)
    if address is not None:
        for row in rows:
            if int(row['start'], 16) <= address < int(row['end_exclusive'], 16):
                return row
        raise ValueError(f'address outside mapped ROM: {query}')

    lowered = query.lower()
    exact = [
        row for row in rows
        if row['unit_id'].lower() == lowered or row['symbol'].lower() == lowered
    ]
    if exact:
        return exact[0]
    partial = [
        row for row in rows
        if lowered in row['unit_id'].lower() or lowered in row['symbol'].lower()
    ]
    if not partial:
        raise ValueError(f'no ROM mapping matches {query!r}')
    return partial[0]


def describe(row: dict) -> str:
    lines = [
        f"ROM:      {row['start']}–{row['end_exclusive']} ({row['bytes']} bytes)",
        f"Section:  {row['section']}",
        f"Symbol:   {row['symbol'] or 'none'}",
        f"Unit:     {row['unit_id'] or 'none'}",
        f"Status:   {row['status']}",
    ]
    if row['relationship']:
        lines.append(
            f"Link:     {row['relationship']} ({row['mapping_confidence']})"
        )
    if row['claim']:
        lines.append(f"Claim:    {row['claim']}")
    if row['source_file']:
        lines.append(f"Assembly: {row['source_file']}:{row['source_line']}")
        lines.append(f"           {row['source_text']}")
    if row['native_location']:
        lines.append(f"Native:   {row['native_location']}")
    if row['notes']:
        lines.append(f"Notes:    {row['notes']}")
    return '\n'.join(lines)


def native_path(row: dict, repo_root: Path) -> tuple[Path, int]:
    location = row['native_location'].split(';', 1)[0]
    if not location:
        raise ValueError('mapping has no native target')
    path_and_line = location.split('#', 1)[0]
    match = re.fullmatch(r'(.*):(\d+)', path_and_line)
    if match:
        return (repo_root / match[1]).resolve(), int(match[2])
    return (repo_root / path_and_line).resolve(), 1


def open_target(args, row: dict) -> None:
    manifest = load_manifest(args.manifest)
    repo_root = manifest.path.parent.parent
    if args.target == 'asm':
        if not row['source_file']:
            raise ValueError('mapping has no assembly source target')
        path = (args.reference_root / row['source_file']).resolve()
        line = int(row['source_line'])
        command = ['code', '--reuse-window', '--goto', f'{path}:{line}']
    elif args.target == 'native':
        path, line = native_path(row, repo_root)
        command = ['code', '--reuse-window', '--goto', f'{path}:{line}']
    elif args.target == 'rom':
        command = ['code', '--reuse-window', str(args.rom.resolve())]
    else:
        command = ['xdg-open', str(args.report.resolve())]
    subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> int:
    parser = argparse.ArgumentParser(description='Query and navigate GBRE mappings')
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--rom-map', type=Path, required=True)
    subparsers = parser.add_subparsers(dest='command', required=True)

    lookup = subparsers.add_parser('lookup')
    lookup.add_argument('query')

    opener = subparsers.add_parser('open')
    opener.add_argument('query')
    opener.add_argument('--target', choices=['asm', 'native', 'rom', 'report'], required=True)
    opener.add_argument('--reference-root', type=Path)
    opener.add_argument('--rom', type=Path)
    opener.add_argument('--report', type=Path)
    args = parser.parse_args()

    row = find_row(read_rows(args.rom_map), args.query)
    if args.command == 'lookup':
        print(describe(row))
        return 0
    if args.target == 'asm' and not args.reference_root:
        parser.error('--reference-root is required for an assembly target')
    if args.target == 'rom' and not args.rom:
        parser.error('--rom is required for a ROM target')
    if args.target == 'report' and not args.report:
        parser.error('--report is required for a report target')
    open_target(args, row)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
