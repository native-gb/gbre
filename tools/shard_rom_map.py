#!/usr/bin/env python3

import argparse
import csv
import tempfile
from pathlib import Path


def parse_size(value: str) -> int:
    return int(value, 0)


def shard_rom_map(
    source_path: Path,
    output_directory: Path,
    bank_size: int,
    expected_rom_size: int | None = None,
) -> tuple[int, int]:
    if bank_size <= 0:
        raise ValueError('bank size must be positive')
    output_directory.parent.mkdir(parents=True, exist_ok=True)
    writers: dict[int, csv.DictWriter] = {}
    handles = {}
    cursor = 0
    output_rows = 0

    with tempfile.TemporaryDirectory(
        prefix=f'.{output_directory.name}-', dir=output_directory.parent
    ) as temporary:
        temporary_path = Path(temporary)
        try:
            with source_path.open(newline='') as source:
                reader = csv.DictReader(source)
                if not reader.fieldnames:
                    raise ValueError('ROM map has no CSV header')
                required = {'start', 'end_exclusive', 'bytes'}
                if not required.issubset(reader.fieldnames):
                    raise ValueError('ROM map is missing interval columns')

                for row in reader:
                    start = int(row['start'], 16)
                    end = int(row['end_exclusive'], 16)
                    if start != cursor or end <= start:
                        raise ValueError(f'invalid ROM-map coverage at ${cursor:X}')
                    while start < end:
                        bank = start // bank_size
                        fragment_end = min(end, (bank + 1) * bank_size)
                        writer = writers.get(bank)
                        if writer is None:
                            handle = (
                                temporary_path / f'bank-{bank:02X}.csv'
                            ).open('w', newline='')
                            handles[bank] = handle
                            writer = csv.DictWriter(
                                handle,
                                fieldnames=reader.fieldnames,
                                lineterminator='\n',
                            )
                            writer.writeheader()
                            writers[bank] = writer
                        fragment = dict(row)
                        fragment['start'] = f'0x{start:04X}'
                        fragment['end_exclusive'] = f'0x{fragment_end:04X}'
                        fragment['bytes'] = str(fragment_end - start)
                        writer.writerow(fragment)
                        output_rows += 1
                        start = fragment_end
                    cursor = end
        finally:
            for handle in handles.values():
                handle.close()

        if expected_rom_size is not None and cursor != expected_rom_size:
            raise ValueError(
                f'coverage ends at ${cursor:X}, expected ${expected_rom_size:X}'
            )
        if not writers:
            raise ValueError('ROM map has no data rows')

        output_directory.mkdir(parents=True, exist_ok=True)
        for old_part in output_directory.glob('bank-*.csv'):
            old_part.unlink()
        for part in sorted(temporary_path.glob('bank-*.csv')):
            part.replace(output_directory / part.name)

    return len(writers), output_rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Split a gapless ROM-map CSV at fixed bank boundaries'
    )
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    parser.add_argument('--bank-size', type=parse_size, required=True)
    parser.add_argument('--rom-size', type=parse_size)
    args = parser.parse_args()

    banks, rows = shard_rom_map(
        args.input,
        args.output_directory,
        args.bank_size,
        args.rom_size,
    )
    print(f'Wrote {rows} rows across {banks} bank shards')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
