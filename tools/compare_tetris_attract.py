#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def load_frames(path: Path) -> list[dict]:
    frames = []
    with path.open() as source:
        for line_number, line in enumerate(source, 1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f'{path}:{line_number}: {error}') from error
            if record.get('kind') == 'frame':
                frames.append(record)
    return frames


def original_active(record: dict) -> tuple[int, int, int]:
    active = record['active']
    return active[3], (active[2] - 39) // 8, (active[1] - 32) // 8


def occupied_cells(board: str, empty: str) -> tuple[bool, ...]:
    return tuple(board[index:index + 2] != empty for index in range(0, len(board), 2))


def first_index(records: list[dict], predicate) -> int | None:
    for index, record in enumerate(records):
        if predicate(record):
            return index
    return None


def compare_attract(original: list[dict], native: list[dict]) -> list[str]:
    errors = []
    original_start = first_index(
        original,
        lambda record: record.get('game_state') == 0 and record.get('demo_number') == 2,
    )
    native_start = first_index(
        native,
        lambda record: record.get('screen') == 'DemoGameplay' and
        record.get('demo_type_b') is False,
    )
    if original_start is None or native_start is None:
        return ['first Type A attract demo is missing from one or both traces']

    # The native trace records the atomic demo setup frame. The first original
    # state-0 record is taken after its first gameplay pass, so align it with the
    # following native frame.
    native_start += 1
    compared = 0
    for relative, original_record in enumerate(original[original_start:]):
        if original_record.get('demo_number') != 2 or original_record.get('game_state') != 0:
            break
        if original_record.get('pieces_played', 0) >= 16:
            break
        native_index = native_start + relative
        if native_index >= len(native):
            errors.append('native trace ends during the Type A attract demo')
            break
        native_record = native[native_index]
        if native_record.get('screen') != 'DemoGameplay':
            errors.append(
                f'attract frame {relative}: native returned to {native_record.get("screen")} early'
            )
            break

        expected_active = original_active(original_record)
        actual_active = tuple(native_record['active'])
        if expected_active != actual_active:
            errors.append(
                f'attract frame {relative}: active piece original={expected_active}, '
                f'native={actual_active}'
            )
            break
        if original_record['lines'][0] != native_record['lines']:
            errors.append(
                f'attract frame {relative}: line count original='
                f'{original_record["lines"][0]}, native={native_record["lines"]}'
            )
            break
        if original_record['drop_timer'] != native_record['drop_timer']:
            errors.append(
                f'attract frame {relative}: drop timer original='
                f'{original_record["drop_timer"]}, native={native_record["drop_timer"]}'
            )
            break

        native_phase = native_record.get('phase')
        presentation_transition = (
            original_record.get('wipe_counter', 0) != 0 or
            native_phase in {'CollapsePending', 'Wiping'}
        )
        if not presentation_transition:
            expected_board = occupied_cells(original_record['board'], '2f')
            actual_board = occupied_cells(native_record['board'], '00')
            if expected_board != actual_board:
                errors.append(f'attract frame {relative}: occupied board cells differ')
                break
        compared += 1

    if compared < 1_700:
        errors.append(f'attract comparison covered only {compared} gameplay frames')

    native_title = first_index(
        native[native_start:],
        lambda record: record.get('screen') == 'Title',
    )
    if native_title is None:
        errors.append('native trace never returns to the title after demo piece 15')
    else:
        title_index = native_start + native_title
        title_record = native[title_index]
        if title_record.get('fixed_pieces_consumed') != 16 or title_record.get('lines') != 4:
            errors.append('native Type A demo did not finish at piece 16 with four cleared lines')

    original_second = first_index(
        original[original_start + compared:],
        lambda record: record.get('game_state') == 0 and record.get('demo_number') == 1,
    )
    native_second = first_index(
        native[native_start + compared:],
        lambda record: record.get('screen') == 'DemoGameplay' and
        record.get('demo_type_b') is True,
    )
    if original_second is None or native_second is None:
        errors.append('short title countdown did not reach the alternating Type B demo')
    elif native[native_start + compared + native_second].get('game_height') != 2:
        errors.append('native Type B attract demo does not retain original height 2')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Compare original and native Tetris attract-mode gameplay.'
    )
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--native', type=Path, required=True)
    arguments = parser.parse_args()
    errors = compare_attract(load_frames(arguments.original), load_frames(arguments.native))
    if errors:
        for error in errors:
            print(f'MISMATCH: {error}')
        return 1
    print('MATCH: full Type A attract demo and alternating Type B entry agree')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
