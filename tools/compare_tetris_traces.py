#!/usr/bin/env python3

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


ORIGINAL_STABLE_SCREENS = {
    0x25: 'CopyrightFixed',
    0x35: 'CopyrightSkippable',
    0x07: 'Title',
    0x0E: 'GameTypeMenu',
    0x0F: 'MusicMenu',
    0x11: 'TypeALevelMenu',
    0x13: 'TypeBLevelMenu',
    0x14: 'TypeBHeightMenu',
    0x17: 'MultiplayerHeightMenu',
}


@dataclass(frozen=True)
class Transition:
    frame: int
    screen: str


def load_json_lines(path: Path) -> list[dict]:
    records = []
    with path.open() as source:
        for line_number, line in enumerate(source, 1):
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f'{path}:{line_number}: {error}') from error
    if not records or records[0].get('kind') != 'metadata':
        raise ValueError(f'{path}: trace has no metadata record')
    return records


def original_transitions(records: list[dict]) -> list[Transition]:
    transitions = []
    last_screen = None
    passed_menu = False
    for record in records:
        if record.get('kind') != 'frame':
            continue
        game_state = record['game_state']
        screen = ORIGINAL_STABLE_SCREENS.get(game_state)
        if game_state == 0:
            if record.get('demo_number', 0) != 0:
                screen = 'DemoGameplay'
            elif passed_menu:
                screen = 'Gameplay'
        if screen is None or screen == last_screen:
            continue
        transitions.append(Transition(record['frame'], screen))
        last_screen = screen
        if screen in {'GameTypeMenu', 'MusicMenu', 'TypeALevelMenu',
                      'TypeBLevelMenu', 'TypeBHeightMenu', 'MultiplayerHeightMenu'}:
            passed_menu = True
    return transitions


def native_transitions(records: list[dict]) -> list[Transition]:
    transitions = []
    last_screen = None
    for record in records:
        if record.get('kind') != 'frame':
            continue
        screen = record['screen']
        if screen == last_screen:
            continue
        transitions.append(Transition(record['frame'], screen))
        last_screen = screen
    return transitions


def compare_transitions(original: list[Transition], native: list[Transition]) -> list[str]:
    errors = []
    count = max(len(original), len(native))
    for index in range(count):
        original_screen = original[index].screen if index < len(original) else '<missing>'
        native_screen = native[index].screen if index < len(native) else '<missing>'
        if original_screen != native_screen:
            errors.append(
                f'transition {index}: original={original_screen}, native={native_screen}'
            )
    return errors


def print_transitions(original: list[Transition], native: list[Transition]) -> None:
    print('index  original frame/screen             native frame/screen')
    count = max(len(original), len(native))
    for index in range(count):
        left = (f'{original[index].frame:5d} {original[index].screen}'
                if index < len(original) else '<missing>')
        right = (f'{native[index].frame:5d} {native[index].screen}'
                 if index < len(native) else '<missing>')
        print(f'{index:5d}  {left:<33} {right}')


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Compare semantic screen transitions in original and native traces.'
    )
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--native', type=Path, required=True)
    arguments = parser.parse_args()

    original = original_transitions(load_json_lines(arguments.original))
    native = native_transitions(load_json_lines(arguments.native))
    print_transitions(original, native)
    errors = compare_transitions(original, native)
    if errors:
        for error in errors:
            print(f'MISMATCH: {error}')
        return 1
    print(f'MATCH: {len(original)} semantic transitions agree')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
