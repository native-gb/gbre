#!/usr/bin/env python3

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

from mgba_service import MgbaService
from scenario_model import Scenario


PIECE_NAMES = {
    0x00: 'L', 0x04: 'J', 0x08: 'I', 0x0C: 'O',
    0x10: 'S', 0x14: 'Z', 0x18: 'T',
}
PHASES = {
    'Falling', 'Locked', 'Resolving', 'Clearing', 'CollapsePending',
    'Wiping', 'GameOver', 'Complete',
}


def native_setup(observation: dict[str, Any]) -> dict[str, Any]:
    game = observation['game']
    selection = observation['selection']
    piece = game['active_piece']
    code = int(piece['code'])
    board = game['board']
    rows = []
    for row in range(18):
        values = board[row * 10:(row + 1) * 10]
        rows.append(''.join('#' if value else '.' for value in values))
    setup = {
        'schema': 'native-gb-tetris.setup.v1',
        'apply_tick': int(observation.get('clock', {}).get('scenario_tick', 0)),
        'game': {
            'mode': selection['mode'],
            'level': game['level'],
            'height': selection['height'],
            'score': game['score'],
            'board': rows,
            'active_piece': {
                'type': PIECE_NAMES.get(code & 0xFC, 'L'),
                'rotation': code & 3,
                'x': piece['x'],
                'y': piece['y'],
            },
        },
    }
    if game.get('phase') in PHASES:
        setup['game']['phase'] = game['phase']
    return setup


def _toml_string(value: str) -> str:
    return json.dumps(value)


def _manifest(identifier: str, source: Scenario) -> str:
    lines = [
        'schema_version = 1',
        f'id = {_toml_string(identifier)}',
        f'title = {_toml_string("Temporary capture of " + source.title)}',
        f'description = {_toml_string("Disposable live capture derived from " + source.id)}',
        'kind = "temporary"',
        'tags = ["temporary", "live-capture"]',
        'subsystems = ["investigation"]',
        '', '[rom]', f'sha1 = "{source.rom_sha1}"',
        '', '[run]', f'frames = {source.frames}',
        '', '[original]',
    ]
    if source.original.input is not None:
        lines.extend([
            'input = "original-input.csv"',
            f'input_mode = "{source.original.input.mode}"',
        ])
    if source.original.patches is not None:
        lines.append('patches = "original-patches.csv"')
    lines.extend([
        '', '[native]', 'setup = "setup.json"',
    ])
    if source.native.input is not None:
        lines.extend([
            'input = "native-input.csv"',
            f'input_mode = "{source.native.input.mode}"',
        ])
    lines.extend([
        '', '[comparison]', 'profile = "fields"',
    ])
    for field in source.fields:
        lines.extend([
            '', '[[comparison.fields]]',
            f'path = {_toml_string(field.path)}',
            f'policy = {_toml_string(field.policy)}',
        ])
        if field.tolerance:
            lines.append(f'tolerance = {field.tolerance}')
        if field.transform != 'identity':
            lines.append(f'transform = {_toml_string(field.transform)}')
        if field.note:
            lines.append(f'note = {_toml_string(field.note)}')
    return '\n'.join(lines) + '\n'


def capture_temporary(scenario_root: Path, scenario: Scenario,
                      native: dict[str, Any], original: dict[str, Any] | None,
                      service: MgbaService | None,
                      recorded_inputs: list[tuple[int, int]] | None = None) -> Path:
    stamp = time.strftime('%Y%m%d-%H%M%S')
    base_identifier = f'temporary.{scenario.id}.{stamp}'
    identifier = base_identifier
    directory = scenario_root.resolve() / '.temporary' / identifier
    suffix = 1
    while directory.exists():
        identifier = f'{base_identifier}-{suffix}'
        directory = scenario_root.resolve() / '.temporary' / identifier
        suffix += 1
    directory.mkdir(parents=True)
    (directory / 'setup.json').write_text(
        json.dumps(native_setup(native), indent=2) + '\n'
    )
    if scenario.original.input is not None:
        shutil.copy2(scenario.original.input.path, directory / 'original-input.csv')
    if scenario.original.patches is not None:
        shutil.copy2(scenario.original.patches, directory / 'original-patches.csv')
    if scenario.native.input is not None:
        shutil.copy2(scenario.native.input.path, directory / 'native-input.csv')
    (directory / 'native-observation.json').write_text(
        json.dumps(native, indent=2) + '\n'
    )
    if original is not None:
        (directory / 'original-observation.json').write_text(
            json.dumps(original, indent=2) + '\n'
        )
    if recorded_inputs:
        (directory / 'live-input.csv').write_text(
            '# Original emulator frame, live Game Boy input mask\n' +
            ''.join(f'{frame},{mask:#04x}\n' for frame, mask in recorded_inputs)
        )
    has_original = original is not None and service is not None
    if has_original:
        service.save_state(directory / 'original.ss0', identifier)
        service.command('capture', directory / 'original.png')
    (directory / 'scenario.toml').write_text(
        _manifest(identifier, scenario)
    )
    return directory
