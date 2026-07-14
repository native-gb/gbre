#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def load_frames(path: Path) -> list[dict]:
    frames = []
    with path.open() as source:
        for line in source:
            record = json.loads(line)
            if record.get('kind') == 'frame':
                frames.append(record)
    return frames


def original_channel(state: list[int], channel: int) -> dict:
    offset = channel * 16
    return {
        'active': state[offset + 1] != 0,
        'timer': state[offset + 2],
        'duration': state[offset + 3],
        'instrument': state[offset + 6:offset + 9],
        'period': state[offset + 9] | (state[offset + 10] << 8),
        'resting': state[offset + 11] != 0,
        'vibrato_counter': state[offset + 14],
        'registers': state[offset + 6:offset + 11],
    }


def compare_music(original: list[dict], native: list[dict], song_id: int) -> list[str]:
    original = [record for record in original if record['frame'] >= 700]
    count = min(len(original), len(native))
    if count == 0:
        return ['music trace has no comparable frames']
    for index in range(count):
        original_record = original[index]
        native_record = native[index]
        original_playing = original_record['current_music'] == song_id
        if original_playing != native_record['playing']:
            return [
                f'song {song_id} tick {index}: original playing={original_playing}, '
                f'native playing={native_record["playing"]}'
            ]
        if not original_playing:
            continue
        for channel in range(4):
            expected = original_channel(original_record['music_state'], channel)
            actual = native_record['channels'][channel]
            if expected['active'] != actual['active']:
                return [
                    f'song {song_id} tick {index} channel {channel + 1} active: '
                    f'original={expected["active"]}, native={actual["active"]}'
                ]
            if not expected['active']:
                continue
            fields = ['timer', 'duration', 'resting', 'vibrato_counter']
            if not expected['resting'] and channel < 3:
                fields.append('instrument')
                fields.append('period')
            if channel == 3 and not expected['resting']:
                fields.append('registers')
            for field in fields:
                if expected[field] != actual[field]:
                    return [
                        f'song {song_id} tick {index} channel {channel + 1} {field}: '
                        f'original={expected[field]}, native={actual[field]}'
                    ]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description='Compare one original music register trace.')
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--song-id', type=int, choices=range(1, 18), required=True)
    arguments = parser.parse_args()
    errors = compare_music(
        load_frames(arguments.original), load_frames(arguments.native), arguments.song_id
    )
    if errors:
        for error in errors:
            print(f'MISMATCH: {error}')
        return 1
    print(f'MATCH: song {arguments.song_id:02d} channel state agrees')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
