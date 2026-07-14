#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


ROCKET_LANDMARKS = (
    (0x0D, 'Game-over curtain'),
    (0x34, 'Rocket bonus delay'),
    (0x2E, 'Rocket graphics initialization'),
    (0x2F, 'Rocket prelaunch'),
    (0x30, 'Rocket ignition'),
    (0x31, 'Rocket liftoff delay'),
    (0x32, 'Rocket rising'),
    (0x33, 'Rocket ending teardown'),
)

BURAN_LANDMARKS = (
    (0x22, 'Type-B victory delay'),
    (0x23, 'Type-B dancers'),
    (0x26, 'Buran graphics initialization'),
    (0x27, 'Buran prelaunch'),
    (0x28, 'Buran ignition'),
    (0x29, 'Buran final ignition'),
    (0x02, 'Buran liftoff'),
    (0x03, 'Buran rising'),
    (0x2C, 'Congratulations text'),
    (0x2D, 'Congratulations wait'),
    (0x0B, 'Scoreboard delay'),
    (0x04, 'Scoreboard wait'),
)

DANCER_CODES = (0x44, 0x4A, 0x46, 0x48, 0x4C, 0x4E, 0x50, 0x52, 0x54, 0x55)
DANCER_Y = (0x3F, 0x3F, 0x3F, 0x77, 0x87, 0x87, 0x67, 0x67, 0x8F, 0x8F)


def load_frames(path: Path) -> dict[int, dict]:
    frames = {}
    with path.open() as source:
        for line in source:
            record = json.loads(line)
            if record.get('kind') == 'frame':
                frames[record['frame']] = record
    return frames


def first_original_state(frames: dict[int, dict], state: int) -> int | None:
    return next((frame for frame, record in frames.items()
                 if frame >= 700 and record['game_state'] == state), None)


def first_native_stage(frames: dict[int, dict], stage: str) -> int | None:
    return next((frame for frame, record in frames.items()
                 if frame >= 700 and record['ending_stage'] == stage), None)


def compare_landmarks(original: dict[int, dict], native: dict[int, dict],
                      landmarks: tuple[tuple[int, str], ...]) -> list[str]:
    errors = []
    for state, stage in landmarks:
        original_frame = first_original_state(original, state)
        native_frame = first_native_stage(native, stage)
        if original_frame != native_frame:
            errors.append(
                f'{stage}: original frame {original_frame}, native frame {native_frame}'
            )
    return errors


def compare_audio(original: dict[int, dict], native: dict[int, dict],
                  last_frame: int) -> list[str]:
    for frame in range(700, last_frame + 1):
        original_song = original[frame]['current_music']
        expected = original_song - 1 if original_song != 0 else -1
        actual = native[frame]['audio_song'] if native[frame]['audio_song_playing'] else -1
        if expected != actual:
            return [f'audio frame {frame}: original ID {original_song}, native index {actual}']
    return []


def compare_launch_positions(original: dict[int, dict], native: dict[int, dict],
                             first_stage: str, last_stage: str) -> list[str]:
    comparing = False
    for frame, record in native.items():
        if record['ending_stage'] == first_stage:
            comparing = True
        if not comparing:
            continue
        original_y = original[frame]['active'][1]
        if original_y != record['launch_y']:
            return [f'launch Y frame {frame}: original {original_y}, native {record["launch_y"]}']
        if record['ending_stage'] in {'Rocket rising', 'Buran rising'}:
            original_exhaust_x = original[frame]['preview'][2]
            if original_exhaust_x != record['exhaust_x']:
                return [
                    f'exhaust X frame {frame}: original {original_exhaust_x}, '
                    f'native {record["exhaust_x"]}'
                ]
            original_exhaust = original[frame]['preview'][1]
            if original_exhaust != record['exhaust_y']:
                return [
                    f'exhaust Y frame {frame}: original {original_exhaust}, '
                    f'native {record["exhaust_y"]}'
                ]
            original_code = original[frame]['preview'][3]
            base_code = 0x5C if record['ending_stage'] == 'Rocket rising' else 0x40
            native_code = base_code + record['exhaust_frame']
            if original_code != native_code:
                return [
                    f'exhaust animation frame {frame}: original {original_code:02X}, '
                    f'native {native_code:02X}'
                ]
        if record['ending_stage'] == last_stage:
            if frame + 1 not in native or native[frame + 1]['ending_stage'] != last_stage:
                break
    return []


def compare_dancers(original: dict[int, dict], native: dict[int, dict]) -> list[str]:
    for frame, record in native.items():
        if record['ending_stage'] != 'Type-B dancers':
            continue
        elapsed = record['ending_elapsed']
        lengths = (28, 15, 30, 50, 32, 24, 38, 29, 40, 43)
        animation_frames = max(elapsed - 26, 0)
        for dancer, (base, length) in enumerate(zip(DANCER_CODES, lengths)):
            alternate = (animation_frames // length) & 1
            expected_code = base ^ alternate
            actual_code = original[frame]['ending_oam'][3 + dancer * 16]
            if expected_code != actual_code:
                return [
                    f'dancer {dancer} frame {frame}: original {actual_code:02X}, '
                    f'native-derived {expected_code:02X}'
                ]
            expected_y = DANCER_Y[dancer] - (10 if dancer == 6 and alternate else 0)
            actual_y = original[frame]['ending_oam'][1 + dancer * 16]
            if expected_y != actual_y:
                return [
                    f'dancer {dancer} Y frame {frame}: original {actual_y:02X}, '
                    f'native-derived {expected_y:02X}'
                ]
    return []


def compare_buran_details(original: dict[int, dict], native: dict[int, dict]) -> list[str]:
    errors = compare_dancers(original, native)
    if errors:
        return errors
    for frame, record in native.items():
        if record['ending_stage'] in {'Congratulations text', 'Congratulations wait'}:
            original_count = max(original[frame]['ending_text_position'][1] - 0x82, 0)
            if original_count != record['congratulations_characters']:
                return [
                    f'congratulations frame {frame}: original {original_count}, '
                    f'native {record["congratulations_characters"]}'
                ]
        if record['screen'] == 'Scoreboard':
            expected_category = original[frame]['scoreboard_state']
            if expected_category != record['scoreboard_category']:
                return [
                    f'scoreboard frame {frame}: original category {expected_category}, '
                    f'native {record["scoreboard_category"]}'
                ]
    return []


def compare_endings(original: dict[int, dict], native: dict[int, dict],
                    scenario: str) -> list[str]:
    if scenario == 'rocket-large':
        errors = compare_landmarks(original, native, ROCKET_LANDMARKS)
        native_name = next((frame for frame, record in native.items()
                            if frame >= 700 and record['screen'] == 'NameEntry'), None)
        original_name = first_original_state(original, 0x15)
        if native_name != original_name:
            errors.append(f'name entry: original frame {original_name}, native frame {native_name}')
        errors += compare_launch_positions(
            original, native, 'Rocket prelaunch', 'Rocket ending teardown'
        )
        errors += compare_audio(original, native, original_name or max(original))
        return errors
    errors = compare_landmarks(original, native, BURAN_LANDMARKS)
    errors += compare_launch_positions(
        original, native, 'Buran prelaunch', 'Buran ending teardown'
    )
    errors += compare_buran_details(original, native)
    errors += compare_audio(original, native, first_original_state(original, 0x04) or max(original))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description='Compare exhaustive original ending traces.')
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--scenario', choices=('rocket-large', 'buran-height-five'), required=True)
    arguments = parser.parse_args()
    errors = compare_endings(
        load_frames(arguments.original), load_frames(arguments.native), arguments.scenario
    )
    if errors:
        for error in errors:
            print(f'MISMATCH: {error}')
        return 1
    print(f'MATCH: {arguments.scenario} ending schedule, animation, audio, and results agree')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
