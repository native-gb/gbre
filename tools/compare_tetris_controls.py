#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def load_frames(path: Path) -> dict[int, dict]:
    frames = {}
    with path.open() as source:
        for line_number, line in enumerate(source, 1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f'{path}:{line_number}: {error}') from error
            if record.get('kind') == 'frame':
                frames[record['frame']] = record
    return frames


def compare_controls(original: dict[int, dict], native: dict[int, dict]) -> list[str]:
    errors = []

    def expect(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    required = {619, 620, 629, 630, 639, 650, 660, 680, 689, 690}
    missing_original = sorted(required - original.keys())
    missing_native = sorted(required - native.keys())
    if missing_original:
        errors.append(f'original trace lacks frames: {missing_original}')
    if missing_native:
        errors.append(f'native trace lacks frames: {missing_native}')
    if missing_original or missing_native:
        return errors

    expect(original[620]['square_sfx'][1] == 4 and native[620]['square_sfx'] == 4,
           'frame 620: horizontal shift must start original square SFX 4')
    expect(original[630]['square_sfx'][1] == 3 and native[630]['square_sfx'] == 3,
           'frame 630: legal rotation must start original square SFX 3')

    original_shift = original[620]['active'][2] - original[619]['active'][2]
    native_shift = native[620]['active'][1] - native[619]['active'][1]
    expect(original_shift == 8 and native_shift == 1,
           'RIGHT must move both representations exactly one board cell')

    original_before_orientation = original[629]['active'][3] & 3
    original_after_orientation = original[630]['active'][3] & 3
    native_before_orientation = native[629]['active'][0] & 3
    native_after_orientation = native[630]['active'][0] & 3
    expect((original_before_orientation, original_after_orientation) == (0, 3) and
           (native_before_orientation, native_after_orientation) == (0, 3),
           'A must rotate the spawn-height piece clockwise from orientation 0 to 3')

    expect(original[650]['active'][1] > original[639]['active'][1] and
           native[650]['active'][2] > native[639]['active'][2],
           'held DOWN must advance the active piece in both traces')
    expect(original[660]['paused'] == 1 and native[660]['audio_paused'] is True,
           'START must pause original and native audio/game state')
    expect(original[680]['paused'] == 0 and native[680]['audio_paused'] is False,
           'the second START edge must resume original and native state')
    expect(original[689]['preview'][0] == 0 and original[690]['preview'][0] == 128 and
           native[689]['preview_hidden'] is False and native[690]['preview_hidden'] is True,
           'SELECT must hide the preview on the same scripted frame')
    expect(original[620]['current_music'] == 5 and native[620]['audio_song'] == 4,
           'both traces must retain Type-A Korobeiniki during control input')

    music_checkpoints = {
        571: 572,
        580: 581,
        590: 591,
        599: 600,
        601: 603,
        610: 612,
        620: 622,
        630: 632,
        650: 652,
        657: 659,
    }
    if all(native_frame in native and original_frame in original and
           'music_base_periods' in native[native_frame] and
           'music_state' in original[original_frame]
           for native_frame, original_frame in music_checkpoints.items()):
        for native_frame, original_frame in music_checkpoints.items():
            original_state = original[original_frame]['music_state']
            original_channels = [
                (original_state[offset + 9] | (original_state[offset + 10] << 8),
                 original_state[offset + 2])
                for offset in (0, 16, 32)
            ]
            native_channels = list(zip(native[native_frame]['music_base_periods'],
                                       native[native_frame]['music_timers']))
            expect(native_channels == original_channels,
                   f'frames native {native_frame}/original {original_frame}: '
                   'music periods and timers must agree across compressed init states')
        expect(original[620]['pan_state'][3] == 3 and
               original[620]['audio_registers'][21] == native[620]['audio_stereo'] == 0xFF,
               'Type-A decoded stereo mode and live routing mask must agree')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Compare scripted Type-A controls and sound cues semantically.'
    )
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--native', type=Path, required=True)
    arguments = parser.parse_args()

    errors = compare_controls(load_frames(arguments.original), load_frames(arguments.native))
    if errors:
        for error in errors:
            print(f'MISMATCH: {error}')
        return 1
    print('MATCH: controls, music periods/timers/stereo, pause, preview, and SFX agree')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
