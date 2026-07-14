#!/usr/bin/env python3

from __future__ import annotations

from typing import Any


STABLE_SCREENS = {
    0x24: 'CopyrightFixed',
    0x25: 'CopyrightFixed',
    0x35: 'CopyrightSkippable',
    0x06: 'Title',
    0x07: 'Title',
    0x0E: 'GameTypeMenu',
    0x0F: 'MusicMenu',
    0x11: 'TypeALevelMenu',
    0x13: 'TypeBLevelMenu',
    0x14: 'TypeBHeightMenu',
    0x17: 'MultiplayerHeightMenu',
    0x15: 'NameEntry',
}

ENDING_STAGES = {
    0x0D: 'Game-over curtain',
    0x34: 'Rocket bonus delay',
    0x2E: 'Rocket graphics initialization',
    0x2F: 'Rocket prelaunch',
    0x30: 'Rocket ignition',
    0x31: 'Rocket liftoff delay',
    0x32: 'Rocket rising',
    0x33: 'Rocket ending teardown',
    0x22: 'Type-B victory delay',
    0x23: 'Type-B dancers',
    0x26: 'Buran graphics initialization',
    0x27: 'Buran prelaunch',
    0x28: 'Buran ignition',
    0x29: 'Buran final ignition',
    0x02: 'Buran liftoff',
    0x03: 'Buran rising',
    0x2C: 'Congratulations text',
    0x2D: 'Congratulations wait',
    0x0B: 'Scoreboard delay',
    0x04: 'Scoreboard wait',
}

MENU_STATES = {0x0E, 0x0F, 0x11, 0x13, 0x14, 0x17}


def _bcd(value: int) -> int:
    return ((value >> 4) & 0xF) * 10 + (value & 0xF)


def _bcd_bytes(values: list[int]) -> int:
    result = 0
    multiplier = 1
    for value in values:
        result += _bcd(value) * multiplier
        multiplier *= 100
    return result


def _board(hexadecimal: str) -> list[int]:
    return [
        0 if hexadecimal[index:index + 2] == '2f' else 1
        for index in range(0, len(hexadecimal), 2)
    ]


def _mode(game_type: int) -> str:
    if game_type == 0x37:
        return 'type-a'
    if game_type == 0x77:
        return 'type-b'
    return 'multiplayer' if game_type == 0 else 'unknown'


def _screen(raw: dict[str, Any], seen_menu: bool) -> str:
    state = raw['game']['state']
    if state in STABLE_SCREENS:
        return STABLE_SCREENS[state]
    if state == 0:
        if raw['game']['demo_number'] != 0:
            return 'DemoGameplay'
        if seen_menu:
            return 'Gameplay'
        return 'CopyrightFixed'
    if state in ENDING_STAGES:
        if state in {0x0B, 0x04}:
            return 'Scoreboard'
        if state in {0x22, 0x23}:
            return 'TypeBDancers'
        if state in {0x26, 0x27, 0x28, 0x29, 0x02, 0x03, 0x2C, 0x2D}:
            return 'BuranEnding'
        return 'RocketEnding'
    return f'OriginalState{state:02X}'


def normalize_original(raw: dict[str, Any], *, seen_menu: bool) -> dict[str, Any]:
    game = raw['game']
    piece = raw['piece']
    active = piece['active']
    audio = raw['audio']
    current_music = audio['current_music']
    selection = raw['selection']
    mode = _mode(selection['game_type'])
    level = (selection['type_a_level'] if mode == 'type-a'
             else selection['type_b_level'])
    active_piece = {
        'code': active[3],
        'x': (active[2] - 39) // 8,
        'y': (active[1] - 32) // 8,
    }
    channels = []
    music_state = audio['music_state']
    for offset in (0, 16, 32, 48):
        channels.append({
            'timer': music_state[offset + 2],
            'period': music_state[offset + 9] | (music_state[offset + 10] << 8),
            'sequence': music_state[offset + 12] | (music_state[offset + 13] << 8),
        })
    return {
        'schema': 'gbre.observation.v1',
        'events_schema': 'gbre.events.v1',
        'side': 'original',
        'clock': {'emulator_frame': raw['clock']['emulator_frame']},
        'screen': _screen(raw, seen_menu),
        'selection': {
            'mode': mode,
            'music': selection['music_type'] - 0x1C,
            'level': level,
            'height': selection['type_b_height'],
        },
        'game': {
            'phase': f'OriginalState{game["state"]:02X}',
            'level': game['level'],
            'lines': _bcd_bytes(game['lines']),
            'score': _bcd_bytes(game['score']),
            'board': _board(game['board_hex']),
            'active_piece': active_piece,
            'preview_piece': piece['next_preview_piece'],
            'preview_hidden': piece['preview'][0] != 0,
            'pieces_played': game['pieces_played'],
            'paused': game['paused'] != 0,
            'tick': raw['clock']['emulator_frame'],
        },
        'events': [],
        'timing': raw['timing'],
        'ending': {
            'stage': ENDING_STAGES.get(game['state'], 'None'),
            'text_position': raw['ending']['text_position'],
            'oam': raw['ending']['oam'],
        },
        'audio': {
            'song': current_music - 1 if current_music else -1,
            'playing': current_music != 0,
            'paused': game['paused'] != 0,
            'stereo': audio['registers'][21],
            'channels': channels,
            'square_sfx': audio['square_sfx'][1],
            'wave_sfx': audio['wave_sfx'][1],
            'noise_sfx': audio['noise_sfx'][1],
        },
        'geometry': {
            'active_oam': active,
            'preview_oam': piece['preview'],
            'ending_oam': raw['ending']['oam'],
        },
        'original': {
            'state': game['state'],
            'pc': raw['hardware']['pc'],
            'sp': raw['hardware']['sp'],
        },
    }
