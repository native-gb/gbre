#!/usr/bin/env python3

import csv
import sys
import unittest
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SML_RE = REPO.parent / 'native-gb-super-mario-land-re'
sys.path.insert(0, str(REPO / 'tools'))

from gbre_common import load_manifest  # noqa: E402
from scenario_inputs import load_strict_inputs  # noqa: E402
from scenario_model import discover_scenarios  # noqa: E402


class SmlResearchIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.manifest_path = SML_RE / 'analysis/sml-rev-a-manifest.json'
        if not self.manifest_path.is_file():
            self.skipTest('private Super Mario Land research database is absent')
        self.manifest = load_manifest(self.manifest_path)

    def test_manifest_identifies_banked_rev_a_rom(self):
        self.assertEqual(self.manifest.rom_size, 0x10000)
        self.assertEqual(
            self.manifest.sha1,
            '418203621b887caa090215d97e3f509b79affd3e',
        )
        self.assertEqual(self.manifest.addressing, 'linear-banked-rom')

    def test_exact_source_map_classifies_every_emitted_byte(self):
        path = SML_RE / 'analysis/sml-rev-a-source-map.csv'
        if not path.is_file():
            self.skipTest('generated SML source map is absent')
        totals = Counter()
        with path.open(newline='') as source:
            for row in csv.DictReader(source):
                totals[row['evidence_kind']] += int(row['bytes'])
                self.assertEqual(row['source_text'], '')

        self.assertEqual(sum(totals.values()), 65_105)
        self.assertEqual(totals['rgbds_assembly'], 23_177)
        self.assertEqual(totals['rgbds_incbin'], 41_790)
        self.assertEqual(totals['rgbds_reserved'], 138)

    def test_rom_map_is_gapless_and_bank_two_addresses_are_linear(self):
        path = SML_RE / 'analysis/sml-rev-a-rom-map.csv'
        cursor = 0
        enemy_row = None
        with path.open(newline='') as source:
            for row in csv.DictReader(source):
                start = int(row['start'], 16)
                end = int(row['end_exclusive'], 16)
                self.assertEqual(start, cursor)
                cursor = end
                if start == 0xA002:
                    enemy_row = row

        self.assertEqual(cursor, 0x10000)
        self.assertIsNotNone(enemy_row)
        self.assertEqual(enemy_row['symbol'], 'level_1_1_enemies')
        self.assertEqual(enemy_row['source_file'], 'levels/enemy_locations.asm')

    def test_native_anchors_exist_and_are_unique(self):
        root = self.manifest.path.parent.parent
        for unit in self.manifest.units:
            for target in unit.native:
                text = (root / target.path).resolve().read_text()
                self.assertEqual(text.count(target.anchor), 1, unit.id)

    def test_curated_sml_scenarios_are_readable_and_rom_bound(self):
        scenario_root = SML_RE / 'scenarios'
        scenarios = discover_scenarios(scenario_root)
        self.assertEqual(
            [scenario.id for scenario in scenarios],
            [
                'sml.block-hit-chibibo',
                'sml.block-hit-fly',
                'sml.block-hit-gao',
                'sml.block-hit-nokobon',
                'sml.breakable-block',
                'sml.chibibo-stomp',
                'sml.crouch',
                'sml.damage-restart',
                'sml.empty-block',
                'sml.expert-opening-spawns',
                'sml.first-power-up',
                'sml.fly-script',
                'sml.fly-stomp',
                'sml.game-over',
                'sml.gao-projectile',
                'sml.gao-stomp',
                'sml.goal-bonus',
                'sml.goal-next-level',
                'sml.heart',
                'sml.hidden-power-up',
                'sml.horizontal-platform-carry',
                'sml.invincible-chibibo',
                'sml.invincible-gao',
                'sml.invincible-second-pipe-room',
                'sml.multi-coin',
                'sml.nokobon-script',
                'sml.nokobon-stomp-bomb',
                'sml.opening-obstacles',
                'sml.pipe-room',
                'sml.plain-block-small',
                'sml.second-pipe-room',
                'sml.star',
                'sml.super-damage',
                'sml.super-flower',
                'sml.superball',
                'sml.superball-chibibo',
                'sml.superball-fly',
                'sml.superball-gao',
                'sml.superball-nokobon',
                'sml.title-start',
                'sml.vertical-platform-carry',
                'sml.walk-jump-camera',
            ],
        )
        for scenario in scenarios:
            self.assertEqual(scenario.rom_sha1, self.manifest.sha1)
            self.assertEqual(scenario.original.adapter, 'sml')
            self.assertEqual(scenario.native.adapter, 'sml')
            self.assertGreater(len(load_strict_inputs(scenario.original.input.path)), 1)


if __name__ == '__main__':
    unittest.main()
