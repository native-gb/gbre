#!/usr/bin/env python3

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TETRIS_RE = REPO.parent / 'native-gb-tetris-re'
sys.path.insert(0, str(REPO / 'tools'))

from gbre_common import load_manifest  # noqa: E402
from compare_tetris_traces import (  # noqa: E402
    Transition,
    compare_transitions,
    native_transitions,
    original_transitions,
)
from compare_tetris_controls import compare_controls  # noqa: E402
from compare_tetris_attract import compare_attract  # noqa: E402
from compare_tetris_endings import (  # noqa: E402
    DANCER_CODES,
    DANCER_Y,
    ROCKET_LANDMARKS,
    compare_dancers,
    compare_launch_positions,
    compare_landmarks,
)
from compare_tetris_music import compare_music  # noqa: E402


class GbreToolsTest(unittest.TestCase):
    def setUp(self):
        self.manifest_path = TETRIS_RE / 'analysis/tetris-v1.1-manifest.json'
        if not self.manifest_path.is_file():
            self.skipTest('private Tetris integration database is absent')
        self.manifest = load_manifest(self.manifest_path)

    def test_manifest_has_stable_units(self):
        self.assertEqual(self.manifest.rom_size, 0x8000)
        self.assertEqual(self.manifest.sha1, '74591cc9501af93873f9a5d3eb12da12c0723bbc')
        self.assertEqual(
            [unit.id for unit in self.manifest.units],
            [
                'tetris.platform_runtime',
                'tetris.next_piece',
                'tetris.rotate_and_shift_piece',
                'tetris.gravity_table',
                'tetris.init_garbage',
                'tetris.drop_piece',
                'tetris.demo_data',
                'tetris.game_flow',
                'tetris.single_player_endings',
                'tetris.collision_and_lock',
                'tetris.line_resolution',
                'tetris.scoring',
                'tetris.high_scores',
                'tetris.multiplayer',
                'tetris.original_tilemaps',
                'tetris.original_presentation_data',
                'tetris.original_metasprites',
                'tetris.tetromino_sprite_data',
                'tetris.original_graphics',
                'tetris.original_audio_data',
                'tetris.original_sound_effects',
                'tetris.original_music_playback',
            ],
        )

    def test_exact_source_map_owns_every_allocated_byte(self):
        path = TETRIS_RE / 'analysis/tetris-v1.1-source-map.csv'
        if not path.exists():
            self.skipTest('generated exact source map is absent')
        byte_count = 0
        with path.open(newline='') as source:
            for row in csv.DictReader(source):
                start = int(row['start'], 16)
                end = int(row['end_exclusive'], 16)
                self.assertGreater(end, start)
                self.assertTrue(row['source_file'])
                self.assertGreater(int(row['source_line']), 0)
                byte_count += end - start
        self.assertEqual(byte_count, 32711)

    def test_rom_map_is_gapless(self):
        path = TETRIS_RE / 'analysis/tetris-v1.1-rom-map.csv'
        cursor = 0
        statuses = {}
        with path.open(newline='') as source:
            for row in csv.DictReader(source):
                start = int(row['start'], 16)
                end = int(row['end_exclusive'], 16)
                self.assertEqual(start, cursor)
                cursor = end
                statuses[row['status']] = statuses.get(row['status'], 0) + end - start
        self.assertEqual(cursor, 0x8000)
        self.assertNotIn('unknown', statuses)
        self.assertEqual(statuses['not_runtime'], 57)
        self.assertEqual(statuses['documented'], 661)
        self.assertEqual(statuses['ported'], 9297)
        self.assertEqual(statuses['excluded'], 858)
        self.assertEqual(statuses['verified'], 21895)

    def test_native_and_derivation_coverage_are_separate(self):
        totals = {}
        path = TETRIS_RE / 'analysis/tetris-v1.1-rom-map.csv'
        with path.open(newline='') as source:
            for row in csv.DictReader(source):
                relationship = row['relationship'] or 'unmapped'
                totals[relationship] = totals.get(relationship, 0) + int(row['bytes'])
        self.assertEqual(totals['implements'], 31234)
        self.assertEqual(totals['derived_from'], 637)

    def test_native_anchors_exist_and_are_unique(self):
        root = self.manifest.path.parent.parent
        for unit in self.manifest.units:
            for target in unit.native:
                text = (root / target.path).resolve().read_text()
                self.assertEqual(text.count(target.anchor), 1, f'{unit.id}: {target.anchor}')

    def test_no_disassembly_still_produces_complete_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'map.csv'
            subprocess.run(
                [
                    sys.executable,
                    str(REPO / 'tools/build_rom_map.py'),
                    '--manifest',
                    str(self.manifest_path),
                    '--output',
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            with output.open(newline='') as source:
                rows = list(csv.DictReader(source))
            self.assertEqual(int(rows[0]['start'], 16), 0)
            self.assertEqual(int(rows[-1]['end_exclusive'], 16), 0x8000)
            self.assertTrue(all(not row['source_file'] for row in rows))

    def test_cli_resolves_semantic_unit(self):
        result = subprocess.run(
            [
                sys.executable,
                str(REPO / 'tools/gbre.py'),
                '--manifest',
                str(self.manifest_path),
                '--rom-map',
                str(TETRIS_RE / 'analysis/tetris-v1.1-rom-map.csv'),
                'lookup',
                'tetris.next_piece',
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('tetris.asm:5079', result.stdout)
        self.assertIn('choose_next_piece', result.stdout)

    def test_oracle_transition_comparison_ignores_original_init_states(self):
        original = [
            {'kind': 'metadata'},
            {'kind': 'frame', 'frame': 0, 'game_state': 0},
            {'kind': 'frame', 'frame': 7, 'game_state': 0x24},
            {'kind': 'frame', 'frame': 11, 'game_state': 0x25},
            {'kind': 'frame', 'frame': 260, 'game_state': 0x35},
            {'kind': 'frame', 'frame': 510, 'game_state': 0x06},
            {'kind': 'frame', 'frame': 515, 'game_state': 0x07},
            {'kind': 'frame', 'frame': 545, 'game_state': 0x0E},
            {'kind': 'frame', 'frame': 572, 'game_state': 0x11},
            {'kind': 'frame', 'frame': 603, 'game_state': 0x00},
        ]
        native = [
            {'kind': 'metadata'},
            {'kind': 'frame', 'frame': 0, 'screen': 'CopyrightFixed'},
            {'kind': 'frame', 'frame': 249, 'screen': 'CopyrightSkippable'},
            {'kind': 'frame', 'frame': 499, 'screen': 'Title'},
            {'kind': 'frame', 'frame': 540, 'screen': 'GameTypeMenu'},
            {'kind': 'frame', 'frame': 570, 'screen': 'TypeALevelMenu'},
            {'kind': 'frame', 'frame': 600, 'screen': 'Gameplay'},
        ]
        original_result = original_transitions(original)
        native_result = native_transitions(native)
        self.assertEqual(
            [item.screen for item in original_result],
            [item.screen for item in native_result],
        )
        self.assertEqual(compare_transitions(original_result, native_result), [])
        self.assertEqual(original_result[0], Transition(11, 'CopyrightFixed'))

    def test_control_comparison_normalizes_native_and_oam_coordinates(self):
        required = {619, 620, 629, 630, 639, 650, 660, 680, 689, 690}
        original = {
            frame: {
                'active': [0, 24, 63, 12],
                'preview': [0],
                'square_sfx': [0, 0],
                'paused': 0,
                'current_music': 5,
            }
            for frame in required
        }
        native = {
            frame: {
                'active': [8, 3, -1],
                'square_sfx': 0,
                'audio_paused': False,
                'preview_hidden': False,
                'audio_song': 4,
            }
            for frame in required
        }
        original[620]['active'][2] = 71
        native[620]['active'][1] = 4
        original[620]['square_sfx'][1] = 4
        native[620]['square_sfx'] = 4
        original[630]['active'][3] = 15
        native[630]['active'][0] = 11
        original[630]['square_sfx'][1] = 3
        native[630]['square_sfx'] = 3
        original[650]['active'][1] = 56
        native[650]['active'][2] = 3
        original[660]['paused'] = 1
        native[660]['audio_paused'] = True
        original[690]['preview'][0] = 128
        native[690]['preview_hidden'] = True
        self.assertEqual(compare_controls(original, native), [])

    def test_attract_comparison_requires_both_recorded_demo_types(self):
        original = [
            {
                'kind': 'frame', 'frame': index, 'game_state': 0, 'demo_number': 2,
                'pieces_played': 3, 'active': [0, 24, 63, 24], 'lines': [0, 0],
                'drop_timer': 9, 'wipe_counter': 0, 'board': '2f' * 180,
            }
            for index in range(1_701)
        ]
        original.append({
            'kind': 'frame', 'frame': 1_701, 'game_state': 0,
            'demo_number': 1, 'pieces_played': 17,
        })
        native = [{
            'kind': 'frame', 'frame': 0, 'screen': 'DemoGameplay',
            'demo_type_b': False,
        }]
        native.extend({
            'kind': 'frame', 'frame': index + 1, 'screen': 'DemoGameplay',
            'demo_type_b': False, 'active': [24, 3, -1], 'lines': 0,
            'drop_timer': 9, 'phase': 'Falling', 'board': '00' * 180,
        } for index in range(1_701))
        native.append({
            'kind': 'frame', 'frame': 1_702, 'screen': 'DemoGameplay',
            'demo_type_b': False, 'fixed_pieces_consumed': 16, 'lines': 4,
        })
        native.append({
            'kind': 'frame', 'frame': 1_703, 'screen': 'Title',
            'demo_type_b': False, 'fixed_pieces_consumed': 16, 'lines': 4,
        })
        native.append({
            'kind': 'frame', 'frame': 1_704, 'screen': 'DemoGameplay',
            'demo_type_b': True, 'game_height': 2,
        })
        self.assertEqual(compare_attract(original, native), [])

    def test_ending_comparison_preserves_measured_initializer_states(self):
        original = {}
        native = {}
        for index, (game_state, ending_stage) in enumerate(ROCKET_LANDMARKS):
            frame = 700 + index * 10
            original[frame] = {'game_state': game_state}
            native[frame] = {'ending_stage': ending_stage}
        self.assertEqual(
            compare_landmarks(original, native, ROCKET_LANDMARKS), []
        )

    def test_ending_comparison_checks_exhaust_position_and_animation(self):
        original = {
            700: {
                'active': [0, 0x6A, 0x57, 0x58],
                'preview': [0, 0x7A, 0x54, 0x5C],
            },
        }
        native = {
            700: {
                'ending_stage': 'Rocket rising',
                'launch_y': 0x6A,
                'exhaust_x': 0x54,
                'exhaust_y': 0x7A,
                'exhaust_frame': 0,
            },
        }
        self.assertEqual(
            compare_launch_positions(
                original, native, 'Rocket rising', 'Rocket rising'),
            [],
        )
        native[700]['exhaust_frame'] = 1
        self.assertIn(
            'exhaust animation',
            compare_launch_positions(
                original, native, 'Rocket rising', 'Rocket rising')[0],
        )

    def test_dancer_comparison_checks_the_cossack_jump(self):
        elapsed = 64
        lengths = (28, 15, 30, 50, 32, 24, 38, 29, 40, 43)
        oam = [0] * 160
        for dancer, (base, length) in enumerate(zip(DANCER_CODES, lengths)):
            alternate = ((elapsed - 26) // length) & 1
            oam[3 + dancer * 16] = base ^ alternate
            oam[1 + dancer * 16] = (
                DANCER_Y[dancer] - (10 if dancer == 6 and alternate else 0)
            )
        original = {700: {'ending_oam': oam}}
        native = {700: {
            'ending_stage': 'Type-B dancers',
            'ending_elapsed': elapsed,
        }}
        self.assertEqual(compare_dancers(original, native), [])
        original[700]['ending_oam'][1 + 6 * 16] += 10
        self.assertIn('dancer 6 Y', compare_dancers(original, native)[0])

    def test_music_comparison_ignores_inactive_channel_workspace(self):
        music_state = [0] * 64
        music_state[3] = 99
        music_state[6:11] = [1, 2, 3, 4, 5]
        original = [{
            'kind': 'frame', 'frame': 700, 'current_music': 1,
            'music_state': music_state,
        }]
        inactive = {
            'active': False, 'timer': 1, 'duration': 1, 'resting': False,
            'vibrato_counter': 0, 'instrument': [0, 0, 0],
            'period': 0, 'registers': [0, 0, 0, 0, 0],
        }
        native = [{
            'kind': 'frame', 'frame': 0, 'playing': True,
            'channels': [inactive.copy() for _ in range(4)],
        }]
        self.assertEqual(compare_music(original, native, 1), [])


if __name__ == '__main__':
    unittest.main()
