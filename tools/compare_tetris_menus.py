#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


LANDMARK_FRAMES = (570, 580, 590, 600, 610, 620, 630, 640,
                   650, 660, 670, 680, 690, 700, 710)


def load_frames(path: Path) -> dict[int, dict]:
    records = {}
    with path.open() as source:
        for line_number, line in enumerate(source, 1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f'{path}:{line_number}: {error}') from error
            if record.get('kind') == 'frame':
                records[record['frame']] = record
    return records


def original_mode(record: dict) -> int:
    game_type = record['game_type']
    if game_type not in (0x37, 0x77):
        raise ValueError(f"unsupported original game-type cursor: {game_type:#04x}")
    return (game_type - 0x37) // 0x40


def original_values(record: dict) -> tuple[int, int, int, int, int]:
    mode = original_mode(record)
    level = record['type_a_level'] if mode == 0 else record['type_b_level']
    current_music = record['current_music']
    song = current_music - 1 if current_music != 0 else -1
    return mode, record['music_type'] - 0x1C, level, record['type_b_height'], song


def native_values(record: dict) -> tuple[int, int, int, int, int]:
    return (record['selected_mode'], record['selected_music'],
            record['selected_level'], record['selected_height'], record['audio_song'])


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Compare menu selections and preview music at scripted landmarks.'
    )
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--native', type=Path, required=True)
    arguments = parser.parse_args()

    original = load_frames(arguments.original)
    native = load_frames(arguments.native)
    errors = []
    print('frame  mode music level height song')
    for frame in LANDMARK_FRAMES:
        if frame not in original or frame not in native:
            errors.append(f'frame {frame}: missing trace record')
            continue
        left = original_values(original[frame])
        right = native_values(native[frame])
        print(f'{frame:5d}  {left} original  {right} native')
        if left != right:
            errors.append(f'frame {frame}: original={left}, native={right}')

    if errors:
        for error in errors:
            print(f'MISMATCH: {error}')
        return 1
    print(f'MATCH: {len(LANDMARK_FRAMES)} menu selection/audio landmarks agree')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
