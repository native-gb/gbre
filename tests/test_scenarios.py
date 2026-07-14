import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'tools'))

from scenario_compare import compare_observations, value_at
from scenario_capture import capture_temporary
from scenario_inputs import condition_matches, load_event_inputs, load_strict_inputs
from scenario_model import ComparisonField, discover_scenarios, find_scenario, load_scenario
from scenario_runner import promote_temporary


SHA1 = '74591cc9501af93873f9a5d3eb12da12c0723bbc'


class ScenarioModelTest(unittest.TestCase):
    def fixture(self, directory: Path, *, schema=1, kind='curated', extra='') -> Path:
        (directory / 'input.csv').write_text('0,NONE\n10,A\n')
        path = directory / 'scenario.toml'
        path.write_text(f'''schema_version = {schema}
id = "test.fixture"
title = "Fixture"
description = "A useful fixture."
kind = "{kind}"
tags = ["gameplay"]
subsystems = ["input"]

[rom]
sha1 = "{SHA1}"

[run]
frames = 20

[original]
input = "input.csv"

[native]
input = "input.csv"

[comparison]
profile = "transitions"
{extra}
''')
        return path

    def test_parses_and_resolves_scenario_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scenario = load_scenario(self.fixture(root))
            self.assertEqual(scenario.id, 'test.fixture')
            self.assertEqual(scenario.original.input.path, (root / 'input.csv').resolve())
            self.assertEqual(scenario.tags, ('gameplay',))

    def test_rejects_unknown_schema_and_bad_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, 'unsupported scenario schema'):
                load_scenario(self.fixture(root, schema=2))
            path = self.fixture(root)
            path.write_text(path.read_text().replace('input.csv', 'missing.csv'))
            with self.assertRaisesRegex(ValueError, 'does not exist'):
                load_scenario(path)

    def test_temporary_scenarios_require_opt_in(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = self.fixture(Path(temporary), kind='temporary')
            with self.assertRaisesRegex(ValueError, 'explicit opt-in'):
                load_scenario(path)
            self.assertEqual(load_scenario(path, allow_temporary=True).kind, 'temporary')

    def test_parameterized_scenario_expands_without_duplicate_manifests(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / 'music'
            directory.mkdir()
            path = self.fixture(directory, kind='parameterized')
            text = path.read_text().replace('id = "test.fixture"', 'id = "test.music.${song_id}"')
            text = text.replace('title = "Fixture"', 'title = "Song ${song_id}"')
            text += '\n[[parameters]]\nname = "song_id"\nvalues = [1, 2, 3]\n'
            path.write_text(text)
            scenarios = discover_scenarios(root)
            self.assertEqual([item.id for item in scenarios],
                             ['test.music.1', 'test.music.2', 'test.music.3'])


class ScenarioInputTest(unittest.TestCase):
    def test_strict_input_validates_order_and_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'strict.csv'
            path.write_text('0,NONE\n10,RIGHT+A\n20,NONE\n')
            events = load_strict_inputs(path)
            self.assertEqual(events[1].keys, ('RIGHT', 'A'))
            path.write_text('10,A\n9,B\n')
            with self.assertRaisesRegex(ValueError, 'must increase'):
                load_strict_inputs(path)

    def test_event_input_and_conditions(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'event.csv'
            path.write_text(
                'action,keys,condition,timeout\n'
                'wait,,screen == Gameplay,600\n'
                'hold,LEFT,active_piece.x <= 0,120\n'
            )
            events = load_event_inputs(path)
            self.assertEqual(events[1].action, 'hold')
            self.assertTrue(condition_matches('active_piece.x <= 0',
                                               {'active_piece': {'x': 0}}))
            self.assertFalse(condition_matches('screen == Gameplay', {'screen': 'Title'}))


class ScenarioComparisonTest(unittest.TestCase):
    def field(self, path, policy, tolerance=0.0, transform='identity', note=''):
        return ComparisonField(path, policy, tolerance, transform, note)

    def test_value_paths_support_members_and_arrays(self):
        self.assertEqual(value_at({'a': {'b': [3, 7]}}, 'a.b[1]'), 7)

    def test_every_comparison_policy(self):
        original = {
            'exact': 3, 'ordered': ['a', 'b'], 'near': 10.0,
            'name': 'GAMEPLAY', 'ignored': 1, 'quirk': 'original',
        }
        native = {
            'exact': 3, 'ordered': ['a', 'b'], 'near': 10.4,
            'name': 'gameplay', 'ignored': 999, 'quirk': 'fixed',
        }
        fields = (
            self.field('exact', 'exact'),
            self.field('ordered', 'ordered'),
            self.field('near', 'tolerance', tolerance=0.5),
            self.field('name', 'transform', transform='lower'),
            self.field('ignored', 'ignore'),
            self.field('quirk', 'intentional_difference', note='fixed by default'),
        )
        result = compare_observations(fields, original, native)
        self.assertTrue(result.matches)
        self.assertEqual(len(result.differences), 1)
        self.assertFalse(result.differences[0].failure)

    def test_reports_actionable_mismatch_and_unknown_transform(self):
        mismatch = compare_observations(
            (self.field('score', 'exact'),), {'score': 10}, {'score': 20}
        )
        self.assertFalse(mismatch.matches)
        self.assertIn('original=10', mismatch.differences[0].message)
        bad = compare_observations(
            (self.field('score', 'transform', transform='missing'),),
            {'score': 10}, {'score': 10},
        )
        self.assertFalse(bad.matches)

        bad_value = compare_observations(
            (self.field('score', 'transform', transform='music_id_to_index'),),
            {'score': 'not-a-number'}, {'score': 10},
        )
        self.assertFalse(bad_value.matches)
        self.assertIn('transform', bad_value.differences[0].message)

        bad_order = compare_observations(
            (self.field('events', 'ordered'),),
            {'events': ['start']}, {'events': 1},
        )
        self.assertFalse(bad_order.matches)


class ScenarioCaptureTest(unittest.TestCase):
    def test_temporary_capture_promotes_readable_rebuildable_fields(self):
        scenario_root = REPO.parent / 'native-gb-tetris-re/scenarios'
        if not scenario_root.is_dir():
            self.skipTest('private Tetris scenario database is absent')
        scenarios = discover_scenarios(scenario_root)
        source = find_scenario(scenarios, 'tetris.start-type-a')
        native = {
            'clock': {'simulation_tick': 3, 'scenario_tick': 600},
            'selection': {'mode': 'type-a', 'height': 0},
            'game': {
                'level': 0, 'score': 40, 'phase': 'Falling',
                'board': [0] * 180,
                'active_piece': {'code': 8, 'x': 3, 'y': 0},
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'scenarios'
            captured = capture_temporary(root, source, native, None, None)
            temporary_scenario = load_scenario(
                captured / 'scenario.toml', allow_temporary=True,
            )
            self.assertEqual(temporary_scenario.kind, 'temporary')
            setup = json.loads((captured / 'setup.json').read_text())
            self.assertEqual(setup['apply_tick'], 600)
            self.assertEqual(setup['game']['active_piece']['type'], 'I')

            curated_root = root / 'curated'
            curated_root.mkdir()
            promoted = promote_temporary(captured, curated_root)
            promoted_scenario = load_scenario(promoted / 'scenario.toml')
            self.assertEqual(promoted_scenario.kind, 'curated')
            self.assertTrue((promoted / 'original-input.csv').is_file())
            self.assertTrue((promoted / 'setup.json').is_file())
            self.assertFalse(any(promoted.glob('*.ss0')))


if __name__ == '__main__':
    unittest.main()
