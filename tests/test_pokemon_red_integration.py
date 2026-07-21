#!/usr/bin/env python3

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
POKEMON_RED_RE = REPO.parent / 'native-gb-pokemon-red-re'
sys.path.insert(0, str(REPO / 'tools'))

from gbre_common import load_manifest, read_rom_map_rows  # noqa: E402


class PokemonRedResearchIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.manifest_path = (
            POKEMON_RED_RE / 'analysis/pokemon-red-ue-manifest.json'
        )
        if not self.manifest_path.is_file():
            self.skipTest('private Pokemon Red research database is absent')
        self.manifest = load_manifest(self.manifest_path)

    def test_manifest_identifies_canonical_english_revision_zero_rom(self):
        self.assertEqual(self.manifest.rom_size, 0x100000)
        self.assertEqual(
            self.manifest.sha1,
            'ea9bcae617fdf159b045185467ae58b2e4a48b9a',
        )
        self.assertEqual(self.manifest.addressing, 'linear-banked-rom')
        self.assertEqual(
            [unit.id for unit in self.manifest.units],
            [
                'pokemon_red.cartridge_header',
                'pokemon_red.moves',
                'pokemon_red.base_stats',
                'pokemon_red.move_names',
                'pokemon_red.internal_species_identity',
                'pokemon_red.type_names',
                'pokemon_red.evolutions_and_level_moves',
                'pokemon_red.items',
                'pokemon_red.tm_hm_catalogue',
                'pokemon_red.encounters',
                'pokemon_red.trainers',
                'pokemon_red.battle_rule_tables',
                'pokemon_red.trainer_move_choice_ai',
                'pokemon_red.map_structure',
                'pokemon_red.toggleable_objects',
                'pokemon_red.map_layout_assets',
                'pokemon_red.tileset_expansion',
                'pokemon_red.resident_collision_cells',
                'pokemon_red.world_tile_policies',
                'pokemon_red.ordinary_field_movement',
                'pokemon_red.party_field_moves',
                'pokemon_red.out_of_battle_poison',
                'pokemon_red.ordinary_wild_encounters',
                'pokemon_red.wild_battle_startup',
                'pokemon_red.ordinary_wild_battle_turns',
                'pokemon_red.level_evolution_resolution',
                'pokemon_red.ordinary_wild_capture_and_inventory',
                'pokemon_red.party_switching_and_participation',
                'pokemon_red.exp_all_reward_distribution',
                'pokemon_red.trainer_shift_set_replacement',
                'pokemon_red.blackout_checkpoint_and_resolution',
                'pokemon_red.major_status_turn_execution',
                'pokemon_red.major_status_move_effects',
                'pokemon_red.stat_stage_move_effects',
                'pokemon_red.badge_and_current_combat_stats',
                'pokemon_red.traded_pokemon_disobedience',
                'pokemon_red.volatile_screen_confusion_recharge',
                'pokemon_red.disable_leech_seed_struggle',
                'pokemon_red.substitute_redirection',
                'pokemon_red.multi_hit_move_execution',
                'pokemon_red.charge_fly_dig_execution',
                'pokemon_red.trapping_move_execution',
                'pokemon_red.thrash_petal_dance_execution',
                'pokemon_red.bide_execution',
                'pokemon_red.rage_execution',
                'pokemon_red.set_damage_move_execution',
                'pokemon_red.ohko_and_jump_kick_execution',
                'pokemon_red.drain_dream_eater_explosion_execution',
                'pokemon_red.counter_and_move_priority_execution',
                'pokemon_red.transform_execution',
                'pokemon_red.mimic_metronome_execution',
                'pokemon_red.mirror_conversion_pay_day_execution',
                'pokemon_red.escape_moves_and_splash_execution',
                'pokemon_red.canonical_move_execution_accountability',
                'pokemon_red.trainer_prize_money',
                'pokemon_red.trainer_action_ai_and_special_moves',
                'pokemon_red.player_battle_items',
                'pokemon_red.special_capture_and_safari_battles',
                'pokemon_red.static_text',
                'pokemon_red.map_text_dispatch',
                'pokemon_red.map_script_dispatch',
                'pokemon_red.pallet_town_script',
                'pokemon_red.pallet_town_movement',
                'pokemon_red.ordinary_map_warps',
                'pokemon_red.dungeon_warps',
                'pokemon_red.oaks_lab_entry',
                'pokemon_red.viridian_mart_parcel',
                'pokemon_red.oaks_parcel_and_pokedex',
                'pokemon_red.blues_house_town_map',
                'pokemon_red.route22_rival_encounters',
                'pokemon_red.route22_boulder_badge_gate',
                'pokemon_red.route23_badge_checkpoints',
                'pokemon_red.victory_road_campaign',
                'pokemon_red.elite_four_champion_campaign',
                'pokemon_red.hall_of_fame_and_credits',
                'pokemon_red.original_save_codec',
                'pokemon_red.application_boot_and_new_game',
                'pokemon_red.opening_field_runtime',
                'pokemon_red.power_plant_and_mewtwo',
                'pokemon_red.cable_club_room_facing',
                'pokemon_red.pewter_museum_and_elevators',
                'pokemon_red.viridian_city_old_man',
                'pokemon_red.ordinary_map_item_pickup',
                'pokemon_red.viridian_forest_trainers',
                'pokemon_red.pewter_gym_brock',
                'pokemon_red.map_trainer_header_catalogue',
                'pokemon_red.route3_trainers',
                'pokemon_red.mt_moon_1f_trainers_and_items',
                'pokemon_red.mt_moon_b2f_fossil_sequence',
                'pokemon_red.route4_trainer_and_item',
                'pokemon_red.route24_nugget_bridge',
                'pokemon_red.route25_trainers_and_bill_handoff',
                'pokemon_red.bills_house_transformation',
                'pokemon_red.cerulean_city_rival_and_rocket',
                'pokemon_red.cerulean_gym_misty',
                'pokemon_red.party_and_trainer_battle_setup',
                'pokemon_red.first_rival_battle_turns',
                'pokemon_red.hidden_items',
                'pokemon_red.daycare',
                'pokemon_red.in_game_trades',
                'pokemon_red.route5_route6_corridor',
                'pokemon_red.vermilion_city_interiors',
                'pokemon_red.ss_anne_campaign',
                'pokemon_red.vermilion_gym_route11',
                'pokemon_red.route9_route10_rock_tunnel',
                'pokemon_red.lavender_town_tower_entry',
                'pokemon_red.pokemon_tower_completion',
                'pokemon_red.celadon_access',
                'pokemon_red.rocket_hideout_campaign',
                'pokemon_red.celadon_gym_interiors',
                'pokemon_red.celadon_commerce',
                'pokemon_red.slot_machine_gameplay',
                'pokemon_red.western_fuchsia_approach',
                'pokemon_red.southern_fuchsia_approach',
                'pokemon_red.fuchsia_city_entry',
                'pokemon_red.fuchsia_gym_koga',
                'pokemon_red.safari_zone_campaign',
                'pokemon_red.saffron_city_entry',
                'pokemon_red.fighting_dojo',
                'pokemon_red.silph_co_campaign',
                'pokemon_red.saffron_gym_sabrina',
                'pokemon_red.southern_sea_routes',
                'pokemon_red.seafoam_islands_campaign',
                'pokemon_red.cinnabar_island_and_lab',
                'pokemon_red.pokemon_mansion_campaign',
                'pokemon_red.cinnabar_gym_blaine',
                'pokemon_red.viridian_gym_giovanni',
                'pokemon_red.field_interaction_and_presentation',
                'pokemon_red.builtin_text_execution',
                'pokemon_red.mart_execution',
                'pokemon_red.pc_systems',
                'pokemon_red.cable_club_reception',
                'pokemon_red.palette_and_sgb_presentation',
                'pokemon_red.raw_graphics_catalogue',
                'pokemon_red.compressed_picture_catalogue',
                'pokemon_red.audio_catalogue_and_command_driver',
                'pokemon_red.gameplay_audio_dispatch',
                'pokemon_red.rgbfix_padding',
            ],
        )

    def test_native_anchors_exist_and_are_unique(self):
        root = self.manifest.path.parent.parent
        for unit in self.manifest.units:
            for target in unit.native:
                text = (root / target.path).resolve().read_text()
                self.assertEqual(text.count(target.anchor), 1, unit.id)

    def test_audio_audit_is_complete_and_bounded(self):
        path = POKEMON_RED_RE / 'analysis/pokemon-red-ue-audio-audit.json'
        if not path.is_file():
            self.skipTest('generated Pokemon Red audio audit is absent')

        audit = json.loads(path.read_text())
        self.assertEqual(
            audit['rom_sha1'],
            'ea9bcae617fdf159b045185467ae58b2e4a48b9a',
        )
        self.assertEqual(audit['audio_banks'], [2, 8, 31])
        self.assertEqual(audit['headers'], 362)
        self.assertEqual(audit['music_headers'], 45)
        self.assertEqual(audit['effect_headers'], 146)
        self.assertEqual(audit['cry_headers'], 114)
        self.assertEqual(audit['noise_instrument_headers'], 57)
        self.assertEqual(audit['header_channels'], 762)
        self.assertEqual(audit['programs'], 785)
        self.assertEqual(audit['header_referenced_programs'], 762)
        self.assertEqual(len(audit['non_header_programs']), 23)
        self.assertEqual(audit['program_bytes'], 36_882)
        self.assertEqual(audit['commands'], 25_501)
        self.assertEqual(sum(audit['command_kinds'].values()), 25_501)
        self.assertEqual(audit['wave_pointer_records'], 27)
        self.assertEqual(audit['wave_samples'], 18)
        self.assertEqual(audit['pitch_tables'], 3)
        self.assertEqual(audit['pitch_records'], 36)
        self.assertEqual(audit['cry_records'], 190)
        self.assertEqual(audit['driver_components'], 8)
        self.assertEqual(audit['driver_bytes'], 8_288)
        self.assertEqual(audit['map_music_records'], 248)
        self.assertEqual(audit['pokedex_rating_sounds'], 7)
        self.assertEqual(audit['battle_music_roles'], 4)
        self.assertEqual(audit['trainer_encounter_music_roles'], 3)
        self.assertEqual(audit['trainer_encounter_explicit_classes'], 12)
        self.assertEqual(audit['trainer_encounter_suppressed_classes'], 3)

    def test_gameplay_audio_dispatch_ranges_are_exact(self):
        units = {unit.id: unit for unit in self.manifest.units}
        dispatch = units['pokemon_red.gameplay_audio_dispatch']
        self.assertEqual(
            {(item.start, item.end) for item in dispatch.rom_ranges},
            {
                (0x033E8, 0x03442),
                (0x090C6, 0x09103),
                (0x0C04D, 0x0C23D),
                (0x7D13B, 0x7D177),
            },
        )
        self.assertEqual(
            {item.path for item in dispatch.source_mappings},
            {
                'data/trainers/encounter_types.asm',
                'audio/play_battle_music.asm',
                'audio/pokedex_rating_sfx.asm',
                'data/maps/songs.asm',
            },
        )

    def test_bookshelf_policy_and_runtime_ranges_are_exact(self):
        units = {unit.id: unit for unit in self.manifest.units}
        world = units['pokemon_red.world_tile_policies']
        field = units['pokemon_red.field_interaction_and_presentation']
        self.assertIn(
            (0x0FB8B, 0x0FBBF),
            {(item.start, item.end) for item in world.rom_ranges},
        )
        self.assertIn(
            'data/tilesets/bookshelf_tile_ids.asm',
            {item.path for item in world.source_mappings},
        )
        field_ranges = {(item.start, item.end) for item in field.rom_ranges}
        self.assertIn((0x03EB5, 0x03EF5), field_ranges)
        self.assertIn((0x0FB50, 0x0FB8B), field_ranges)
        self.assertIn((0x0FBBF, 0x0FC4A), field_ranges)
        self.assertEqual(
            {
                'engine/events/hidden_events/bookshelves.asm',
                'engine/events/hidden_events/indigo_plateau_statues.asm',
                'engine/events/hidden_events/book_or_sculpture.asm',
                'engine/events/hidden_events/elevator.asm',
                'engine/events/hidden_events/town_map.asm',
                'engine/events/hidden_events/pokemon_stuff.asm',
            },
            {item.path for item in field.source_mappings},
        )

    def test_out_of_battle_poison_ranges_are_exact(self):
        units = {unit.id: unit for unit in self.manifest.units}
        poison = units['pokemon_red.out_of_battle_poison']
        self.assertEqual(
            {
                (0x05ED, 0x05F1),
                (0x0620, 0x062C),
                (0x0C33E, 0x0C341),
                (0x0C69C, 0x0C754),
            },
            {(item.start, item.end) for item in poison.rom_ranges},
        )
        self.assertEqual(
            {'engine/events/poison.asm'},
            {item.path for item in poison.source_mappings},
        )

    def test_party_field_move_ranges_are_exact(self):
        units = {unit.id: unit for unit in self.manifest.units}
        world = units['pokemon_red.world_tile_policies']
        field_moves = units['pokemon_red.party_field_moves']
        warps = units['pokemon_red.ordinary_map_warps']
        self.assertIn(
            (0x0F100, 0x0F113),
            {(item.start, item.end) for item in world.rom_ranges},
        )
        self.assertEqual(
            {
                (0x0CD99, 0x0CE04),
                (0x0D9B4, 0x0DA56),
                (0x0E5B6, 0x0E5C0),
                (0x0E5DE, 0x0E5E3),
                (0x0E8B8, 0x0E8E0),
                (0x0EF54, 0x0EFF7),
                (0x0F09F, 0x0F100),
                (0x131C0, 0x131D4),
                (0x131D4, 0x13203),
                (0x13203, 0x13213),
                (0x13213, 0x1322D),
            },
            {(item.start, item.end) for item in field_moves.rom_ranges},
        )
        self.assertEqual(
            {'engine/overworld/field_move_messages.asm'},
            {item.path for item in field_moves.source_mappings},
        )
        self.assertTrue(
            {
                (0x0735, 0x076B),
                (0x079D, 0x07AA),
            }.issubset(
                {(item.start, item.end) for item in warps.rom_ranges}
            )
        )

    def test_safari_field_dispatch_ranges_are_exact(self):
        units = {unit.id: unit for unit in self.manifest.units}
        ordinary = units['pokemon_red.ordinary_wild_encounters']
        safari = units['pokemon_red.safari_zone_campaign']
        self.assertIn(
            (0x03B6, 0x03C2),
            {(item.start, item.end) for item in ordinary.rom_ranges},
        )
        ranges = {(item.start, item.end) for item in safari.rom_ranges}
        self.assertTrue(
            {
                (0x041A, 0x042C),
                (0x0603, 0x061D),
                (0x1E98D, 0x1EA17),
            }.issubset(ranges)
        )

    def test_field_travel_ranges_are_exact(self):
        units = {unit.id: unit for unit in self.manifest.units}
        travel = units['pokemon_red.blackout_checkpoint_and_resolution']
        ranges = {(item.start, item.end) for item in travel.rom_ranges}
        self.assertTrue(
            {
                (0x0965, 0x098F),
                (0x12E7, 0x12ED),
                (0x6346, 0x635B),
                (0x638E, 0x63BF),
                (0x0DFAF, 0x0DFFD),
                (0x1318E, 0x131C0),
                (0x1322D, 0x1328A),
                (0x132DF, 0x132ED),
                (0x71070, 0x71093),
            }.issubset(ranges)
        )

    def test_dungeon_warp_ranges_are_exact(self):
        units = {unit.id: unit for unit in self.manifest.units}
        dungeon = units['pokemon_red.dungeon_warps']
        self.assertEqual(
            {
                (0x6346, 0x638E),
                (0x63BF, 0x63D8),
                (0x63D8, 0x6420),
                (0x44846, 0x4484B),
                (0x449F9, 0x449FE),
                (0x4636D, 0x46372),
                (0x464A9, 0x464AE),
                (0x465F6, 0x465FB),
                (0x46981, 0x469A0),
                (0x52254, 0x5225B),
            },
            {(item.start, item.end) for item in dungeon.rom_ranges},
        )
        self.assertIn(
            'DungeonWarpList',
            dungeon.asm_symbols,
        )

    def test_builtin_nurse_ranges_are_exact(self):
        units = {unit.id: unit for unit in self.manifest.units}
        nurses = units['pokemon_red.builtin_text_execution']
        self.assertEqual(
            {
                (0x06FE9, 0x07078),
                (0x19C89, 0x19C8A),
                (0x4426B, 0x4426C),
                (0x488C7, 0x488C8),
                (0x492E1, 0x492E2),
                (0x493C8, 0x493C9),
                (0x5C595, 0x5C596),
                (0x5C654, 0x5C655),
                (0x5C8E9, 0x5C8EA),
                (0x5C99D, 0x5C99E),
                (0x5D543, 0x5D544),
                (0x75071, 0x75072),
                (0x75E3A, 0x75E3B),
            },
            {(item.start, item.end) for item in nurses.rom_ranges},
        )
        self.assertEqual(
            {
                'engine/events/pokecenter.asm',
                'macros/scripts/text.asm',
            },
            {item.path for item in nurses.source_mappings},
        )

    def test_mart_ranges_are_exact(self):
        units = {unit.id: unit for unit in self.manifest.units}
        marts = units['pokemon_red.mart_execution']
        self.assertEqual(
            {
                (0x02442, 0x0245D),
                (0x0245D, 0x02461),
                (0x02461, 0x024B1),
                (0x024B1, 0x024B9),
                (0x024B9, 0x024D6),
                (0x02A2E, 0x02A72),
                (0x02B96, 0x02BE6),
                (0x02D57, 0x02E3B),
                (0x03040, 0x03049),
                (0x030D9, 0x030E8),
                (0x037DF, 0x03826),
                (0x06B21, 0x06B44),
                (0x06C20, 0x06E43),
                (0x0CE04, 0x0CEB8),
                (0x0F71E, 0x0F836),
                (0x1D47D, 0x1D495),
                (0x1D4E0, 0x1D4F0),
            },
            {(item.start, item.end) for item in marts.rom_ranges},
        )
        self.assertIn('DisplayPokemartDialogue_', marts.asm_symbols)
        self.assertIn('ViridianMart_TextPointers2', marts.asm_symbols)

    def test_celadon_vendor_sources_are_exact(self):
        units = {unit.id: unit for unit in self.manifest.units}
        vendors = units['pokemon_red.celadon_commerce']
        self.assertEqual(
            {
                'data/items/vending_prices.asm',
                'engine/events/vending_machine.asm',
                'data/events/prizes.asm',
                'data/events/prize_mon_levels.asm',
                'engine/events/prize_menu.asm',
            },
            {item.path for item in vendors.source_mappings},
        )
        self.assertIn('VendingPrices', vendors.asm_symbols)
        self.assertIn('PrizeDifferentMenuPtrs', vendors.asm_symbols)
        self.assertIn('PrizeMonLevelDictionary', vendors.asm_symbols)

    def test_pc_ranges_are_exact(self):
        units = {unit.id: unit for unit in self.manifest.units}
        pc = units['pokemon_red.pc_systems']
        self.assertEqual(
            {
                (0x078E6, 0x07B68),
                (0x17E2C, 0x17F37),
                (0x1E915, 0x1E94B),
                (0x213C8, 0x2171B),
                (0x2171B, 0x21745),
                (0x21745, 0x2174B),
                (0x2174B, 0x21825),
                (0x44169, 0x441B6),
                (0x441B6, 0x441CC),
                (0x441CC, 0x44251),
                (0x5DB86, 0x5DB8F),
                (0x62516, 0x6252A),
                (0x7657E, 0x76688),
            },
            {(item.start, item.end) for item in pc.rom_ranges},
        )
        self.assertIn('HMMoveArray', pc.asm_symbols)
        self.assertIn('DexRatingsTable', pc.asm_symbols)
        self.assertIn('OpenPokemonCenterPC', pc.asm_symbols)

    def test_cable_club_reception_ranges_are_exact(self):
        units = {unit.id: unit for unit in self.manifest.units}
        reception = units['pokemon_red.cable_club_reception']
        self.assertEqual(
            {
                (0x05C0A, 0x05D52),
                (0x05D97, 0x05DB5),
                (0x062FF, 0x06326),
                (0x06334, 0x06346),
                (0x06428, 0x06448),
                (0x071C5, 0x072EA),
                (0x19C94, 0x19C95),
                (0x44276, 0x44277),
                (0x488C6, 0x488C7),
                (0x49375, 0x49376),
                (0x493D3, 0x493D4),
                (0x5C60C, 0x5C60D),
                (0x5C653, 0x5C654),
                (0x5C8E8, 0x5C8E9),
                (0x5C9A8, 0x5C9A9),
                (0x5D54E, 0x5D54F),
                (0x7507C, 0x7507D),
                (0x75E45, 0x75E46),
                (0x8A3D0, 0x8A425),
                (0xA292B, 0xA2A37),
                (0xA4000, 0xA403C),
            },
            {(item.start, item.end) for item in reception.rom_ranges},
        )
        self.assertIn('LinkMenu', reception.asm_symbols)
        self.assertIn('CableClubNPC', reception.asm_symbols)
        self.assertIn('TradeCenterPlayerWarp', reception.asm_symbols)

    def test_raw_graphics_ranges_and_map_are_exact(self):
        units = {unit.id: unit for unit in self.manifest.units}
        graphics = units['pokemon_red.raw_graphics_catalogue']
        self.assertEqual(len(graphics.rom_ranges), 45)
        self.assertEqual(
            sum(item.end - item.start for item in graphics.rom_ranges),
            63_280,
        )
        self.assertIn(
            (0x6802F, 0x6867F),
            {(item.start, item.end) for item in graphics.rom_ranges},
        )
        rows = []
        rom_map = POKEMON_RED_RE / 'analysis/pokemon-red-ue-rom-map'
        for path in sorted(rom_map.glob('bank-*.csv')):
            with path.open(newline='') as source:
                rows.extend(
                    row for row in csv.DictReader(source)
                    if row['unit_id'] == graphics.id
                )
        self.assertEqual(len(rows), 151)
        self.assertEqual(sum(int(row['bytes']) for row in rows), 63_280)
        self.assertEqual(
            {
                (
                    row['understanding'], row['native_status'],
                    row['verification'], row['mapping_confidence'],
                )
                for row in rows
            },
            {('documented', 'ported', 'verified', 'exact')},
        )

    def test_palette_sgb_ranges_and_map_are_exact(self):
        units = {unit.id: unit for unit in self.manifest.units}
        palettes = units['pokemon_red.palette_and_sgb_presentation']
        self.assertEqual(
            [(item.start, item.end) for item in palettes.rom_ranges],
            [
                (0x03DDC, 0x03E08),
                (0x71DDF, 0x71FEB),
                (0x71FEB, 0x7219E),
                (0x7219E, 0x72FE8),
            ],
        )
        self.assertEqual(
            sum(item.end - item.start for item in palettes.rom_ranges),
            4_661,
        )
        self.assertEqual(
            [item.relationship for item in palettes.rom_ranges],
            ['implements', 'implements', 'references', 'implements'],
        )
        self.assertEqual(
            palettes.rom_ranges[2].disposition,
            'intentional_change',
        )
        rows = []
        rom_map = POKEMON_RED_RE / 'analysis/pokemon-red-ue-rom-map'
        for path in sorted(rom_map.glob('bank-*.csv')):
            with path.open(newline='') as source:
                rows.extend(
                    row for row in csv.DictReader(source)
                    if row['unit_id'] == palettes.id
                )
        self.assertEqual(len(rows), 921)
        self.assertEqual(sum(int(row['bytes']) for row in rows), 4_661)
        self.assertEqual(
            {
                (
                    row['understanding'], row['native_status'],
                    row['verification'], row['mapping_confidence'],
                )
                for row in rows
            },
            {('documented', 'ported', 'verified', 'exact')},
        )

    def test_compressed_picture_ranges_and_map_are_exact(self):
        units = {unit.id: unit for unit in self.manifest.units}
        pictures = units['pokemon_red.compressed_picture_catalogue']
        self.assertEqual(len(pictures.rom_ranges), 8)
        self.assertEqual(
            sum(item.end - item.start for item in pictures.rom_ranges),
            92_385,
        )
        self.assertIn(
            (0x04112, 0x0425B),
            {(item.start, item.end) for item in pictures.rom_ranges},
        )
        self.assertIn(
            (0x4C000, 0x4FD04),
            {(item.start, item.end) for item in pictures.rom_ranges},
        )
        rows = []
        rom_map = POKEMON_RED_RE / 'analysis/pokemon-red-ue-rom-map'
        for path in sorted(rom_map.glob('bank-*.csv')):
            with path.open(newline='') as source:
                rows.extend(
                    row for row in csv.DictReader(source)
                    if row['unit_id'] == pictures.id
                )
        self.assertEqual(len(rows), 355)
        self.assertEqual(sum(int(row['bytes']) for row in rows), 92_385)
        self.assertEqual(
            {
                (
                    row['understanding'], row['native_status'],
                    row['verification'], row['mapping_confidence'],
                )
                for row in rows
            },
            {('documented', 'ported', 'verified', 'exact')},
        )

    def test_exact_source_map_classifies_every_linker_emitted_byte(self):
        path = POKEMON_RED_RE / 'analysis/pokemon-red-ue-source-map.csv'
        if not path.is_file():
            self.skipTest('generated Pokemon Red source map is absent')

        totals = Counter()
        source_files = set()
        with path.open(newline='') as source:
            for row in csv.DictReader(source):
                totals[row['evidence_kind']] += int(row['bytes'])
                source_files.add(row['source_file'])
                self.assertEqual(row['source_text'], '')

        self.assertEqual(sum(totals.values()), 575_425)
        self.assertEqual(totals['rgbds_assembly'], 376_528)
        self.assertEqual(totals['rgbds_incbin'], 198_225)
        self.assertEqual(totals['rgbds_reserved'], 672)
        self.assertEqual(len(source_files), 1_862)

    def test_rom_map_is_gapless_and_physical_padding_is_explicit(self):
        path = POKEMON_RED_RE / 'analysis/pokemon-red-ue-rom-map'
        if not path.is_dir():
            self.skipTest('generated Pokemon Red ROM map is absent')

        cursor = 0
        status_bytes = Counter()
        padding_sections = Counter()
        last_emitted_row = None
        for row in read_rom_map_rows(path):
            start = int(row['start'], 16)
            end = int(row['end_exclusive'], 16)
            self.assertEqual(start, cursor)
            cursor = end
            status_bytes[row['status']] += end - start
            if row['section'] in ('linker padding', 'rgbfix padding'):
                padding_sections[row['section']] += end - start
            if start == 0xB0606:
                last_emitted_row = row

        self.assertEqual(cursor, 0x100000)
        self.assertEqual(status_bytes['documented'], 0)
        self.assertEqual(status_bytes['excluded'], 311_765)
        self.assertEqual(status_bytes['verified'], 465_906)
        self.assertEqual(status_bytes['unknown'], 270_905)
        self.assertEqual(padding_sections['rgbfix padding'], 311_296)
        self.assertGreater(padding_sections['linker padding'], 0)
        self.assertIsNotNone(last_emitted_row)
        self.assertEqual(
            last_emitted_row['source_file'],
            'data/moves/names.asm',
        )

    def test_content_inventory_accounts_for_every_emitting_source_file(self):
        path = (
            POKEMON_RED_RE /
            'analysis/pokemon-red-ue-content-inventory.csv'
        )
        if not path.is_file():
            self.skipTest('generated Pokemon Red content inventory is absent')

        domain_files = Counter()
        total_spans = 0
        total_bytes = 0
        with path.open(newline='') as source:
            rows = list(csv.DictReader(source))
        for row in rows:
            domain_files[row['domain']] += 1
            total_spans += int(row['span_count'])
            total_bytes += int(row['rom_bytes'])
            implemented_tables = {
                'data/battle/critical_hit_moves.asm',
                'data/battle/stat_modifiers.asm',
                'data/battle/unused_critical_hit_moves.asm',
                'data/events/hidden_item_coords.asm',
                'data/events/prizes.asm',
                'data/events/prize_mon_levels.asm',
                'data/events/slot_machine_wheels.asm',
                'data/credits/credits_mons.asm',
                'data/credits/credits_order.asm',
                'data/credits/credits_text.asm',
                'data/pokemon/palettes.asm',
                'data/sgb/sgb_border.asm',
                'data/sgb/sgb_packets.asm',
                'data/sgb/sgb_palettes.asm',
                'engine/gfx/palettes.asm',
                'data/events/trades.asm',
                'data/moves/moves.asm',
                'data/moves/names.asm',
                'data/moves/tmhm_moves.asm',
                'data/items/key_items.asm',
                'data/items/names.asm',
                'data/items/prices.asm',
                'data/items/tm_prices.asm',
                'data/maps/map_header_banks.asm',
                'data/maps/map_header_pointers.asm',
                'data/maps/rest_house_maps.asm',
                'data/maps/toggleable_objects.asm',
                'data/pokemon/dex_order.asm',
                'data/pokemon/evos_moves.asm',
                'data/pokemon/names.asm',
                'data/trainers/ai_pointers.asm',
                'data/trainers/encounter_types.asm',
                'data/trainers/move_choices.asm',
                'data/trainers/names.asm',
                'data/trainers/parties.asm',
                'data/trainers/pic_pointers_money.asm',
                'data/tilesets/collision_tile_ids.asm',
                'data/tilesets/bike_riding_tilesets.asm',
                'data/tilesets/bookshelf_tile_ids.asm',
                'data/tilesets/door_tile_ids.asm',
                'data/tilesets/dungeon_tilesets.asm',
                'data/tilesets/escape_rope_tilesets.asm',
                'data/tilesets/ledge_tiles.asm',
                'data/tilesets/pair_collision_tile_ids.asm',
                'data/tilesets/tileset_headers.asm',
                'data/tilesets/warp_carpet_tile_ids.asm',
                'data/tilesets/warp_pad_hole_tile_ids.asm',
                'data/tilesets/warp_tile_ids.asm',
                'data/tilesets/water_tilesets.asm',
                'data/types/names.asm',
                'data/types/type_matchups.asm',
                'engine/battle/move_effects/haze.asm',
                'engine/battle/wild_encounters.asm',
                'engine/events/black_out.asm',
                'engine/events/heal_party.asm',
                'engine/events/hidden_events/vermilion_gym_trash.asm',
                'engine/events/oaks_aide.asm',
                'engine/events/pokecenter.asm',
                'engine/events/poison.asm',
                'engine/events/prize_menu.asm',
                'engine/events/set_blackout_map.asm',
                'engine/events/card_key.asm',
                'engine/events/cinnabar_lab.asm',
                'data/events/card_key_maps.asm',
                'data/events/hidden_coins.asm',
                'data/events/hidden_events.asm',
                'engine/events/vending_machine.asm',
                'engine/events/hidden_items.asm',
                'engine/events/hidden_events/book_or_sculpture.asm',
                'engine/events/hidden_events/bookshelves.asm',
                'engine/events/hidden_events/elevator.asm',
                'engine/events/hidden_events/indigo_plateau_statues.asm',
                'engine/events/hidden_events/pokemon_stuff.asm',
                'engine/events/hidden_events/town_map.asm',
                'engine/events/hidden_events/safari_game.asm',
                'engine/events/hidden_events/cinnabar_gym_quiz.asm',
                'engine/overworld/daycare_exp.asm',
                'engine/overworld/field_move_messages.asm',
                'engine/overworld/push_boulder.asm',
                'engine/slots/game_corner_slots.asm',
                'engine/slots/game_corner_slots2.asm',
                'engine/movie/hall_of_fame.asm',
            }
            implemented_scripts = {
                'scripts/Daycare.asm',
                'scripts/PewterCity.asm',
                'scripts/Museum1F.asm',
                'scripts/PalletTown.asm',
                'scripts/TradeCenter.asm',
                'scripts/Colosseum.asm',
                'scripts/Route5.asm',
                'scripts/Route5Gate.asm',
                'scripts/Route6.asm',
                'scripts/Route6Gate.asm',
                'scripts/UndergroundPathRoute5.asm',
                'scripts/UndergroundPathRoute6.asm',
                'scripts/PokemonFanClub.asm',
                'scripts/VermilionCity.asm',
                'scripts/VermilionMart.asm',
                'scripts/VermilionOldRodHouse.asm',
                'scripts/VermilionPidgeyHouse.asm',
                'scripts/VermilionTradeHouse.asm',
                'scripts/SSAnne1F.asm',
                'scripts/SSAnne1FRooms.asm',
                'scripts/SSAnne2F.asm',
                'scripts/SSAnne2FRooms.asm',
                'scripts/SSAnne3F.asm',
                'scripts/SSAnneB1F.asm',
                'scripts/SSAnneB1FRooms.asm',
                'scripts/SSAnneBow.asm',
                'scripts/SSAnneCaptainsRoom.asm',
                'scripts/SSAnneKitchen.asm',
                'scripts/VermilionGym.asm',
                'scripts/Route11.asm',
                'scripts/Route11Gate1F.asm',
                'scripts/Route11Gate2F.asm',
                'scripts/DiglettsCave.asm',
                'scripts/DiglettsCaveRoute11.asm',
                'scripts/Route9.asm',
                'scripts/Route10.asm',
                'scripts/RockTunnel1F.asm',
                'scripts/RockTunnelB1F.asm',
                'scripts/RockTunnelPokecenter.asm',
                'scripts/PowerPlant.asm',
                'scripts/LavenderTown.asm',
                'scripts/LavenderPokecenter.asm',
                'scripts/PokemonTower1F.asm',
                'scripts/PokemonTower2F.asm',
                'scripts/PokemonTower3F.asm',
                'scripts/PokemonTower4F.asm',
                'scripts/PokemonTower5F.asm',
                'scripts/PokemonTower6F.asm',
                'scripts/PokemonTower7F.asm',
                'scripts/MrFujisHouse.asm',
                'scripts/LavenderCuboneHouse.asm',
                'scripts/NameRatersHouse.asm',
                'scripts/LavenderMart.asm',
                'scripts/Route7.asm',
                'scripts/Route8.asm',
                'scripts/Route7Gate.asm',
                'scripts/Route8Gate.asm',
                'scripts/UndergroundPathRoute7.asm',
                'scripts/UndergroundPathRoute8.asm',
                'scripts/CeladonCity.asm',
                'scripts/RocketHideoutB1F.asm',
                'scripts/RocketHideoutB2F.asm',
                'scripts/RocketHideoutB3F.asm',
                'scripts/RocketHideoutB4F.asm',
                'scripts/RocketHideoutElevator.asm',
                'scripts/CeladonGym.asm',
                'scripts/CeladonPokecenter.asm',
                'scripts/CeladonDiner.asm',
                'scripts/CeladonChiefHouse.asm',
                'scripts/CeladonHotel.asm',
                'scripts/CeladonMansion1F.asm',
                'scripts/CeladonMansion2F.asm',
                'scripts/CeladonMansion3F.asm',
                'scripts/CeladonMansionRoof.asm',
                'scripts/CeladonMansionRoofHouse.asm',
                'scripts/CeladonMart1F.asm',
                'scripts/CeladonMart2F.asm',
                'scripts/CeladonMart3F.asm',
                'scripts/CeladonMart4F.asm',
                'scripts/CeladonMart5F.asm',
                'scripts/CeladonMartRoof.asm',
                'scripts/CeladonMartElevator.asm',
                'scripts/GameCorner.asm',
                'scripts/GameCornerPrizeRoom.asm',
                'scripts/Route16.asm',
                'scripts/Route16FlyHouse.asm',
                'scripts/Route16Gate1F.asm',
                'scripts/Route16Gate2F.asm',
                'scripts/Route17.asm',
                'scripts/Route18.asm',
                'scripts/Route18Gate1F.asm',
                'scripts/Route18Gate2F.asm',
                'scripts/Route19.asm',
                'scripts/Route20.asm',
                'scripts/Route21.asm',
                'scripts/SeafoamIslands1F.asm',
                'scripts/SeafoamIslandsB1F.asm',
                'scripts/SeafoamIslandsB2F.asm',
                'scripts/SeafoamIslandsB3F.asm',
                'scripts/SeafoamIslandsB4F.asm',
                'scripts/Route12.asm',
                'scripts/Route13.asm',
                'scripts/Route14.asm',
                'scripts/Route15.asm',
                'scripts/Route12Gate1F.asm',
                'scripts/Route12Gate2F.asm',
                'scripts/Route12SuperRodHouse.asm',
                'scripts/Route15Gate1F.asm',
                'scripts/Route15Gate2F.asm',
                'scripts/FuchsiaCity.asm',
                'scripts/FuchsiaMart.asm',
                'scripts/FuchsiaBillsGrandpasHouse.asm',
                'scripts/FuchsiaPokecenter.asm',
                'scripts/FuchsiaMeetingRoom.asm',
                'scripts/FuchsiaGoodRodHouse.asm',
                'scripts/FuchsiaGym.asm',
                'scripts/SafariZoneGate.asm',
                'scripts/SafariZoneCenter.asm',
                'scripts/SafariZoneEast.asm',
                'scripts/SafariZoneNorth.asm',
                'scripts/SafariZoneWest.asm',
                'scripts/SafariZoneCenterRestHouse.asm',
                'scripts/SafariZoneEastRestHouse.asm',
                'scripts/SafariZoneNorthRestHouse.asm',
                'scripts/SafariZoneWestRestHouse.asm',
                'scripts/SafariZoneSecretHouse.asm',
                'scripts/WardensHouse.asm',
                'scripts/SaffronCity.asm',
                'scripts/SaffronPidgeyHouse.asm',
                'scripts/SaffronMart.asm',
                'scripts/SaffronPokecenter.asm',
                'scripts/MrPsychicsHouse.asm',
                'scripts/SilphCo1F.asm',
                'scripts/FightingDojo.asm',
                'scripts/SilphCo2F.asm',
                'scripts/SilphCo3F.asm',
                'scripts/SilphCo4F.asm',
                'scripts/SilphCo5F.asm',
                'scripts/SilphCo6F.asm',
                'scripts/SilphCo7F.asm',
                'scripts/SilphCo8F.asm',
                'scripts/SilphCo9F.asm',
                'scripts/SilphCo10F.asm',
                'scripts/SilphCo11F.asm',
                'scripts/SilphCoElevator.asm',
                'scripts/CeruleanCaveB1F.asm',
                'scripts/SaffronGym.asm',
                'scripts/CinnabarIsland.asm',
                'scripts/CinnabarLab.asm',
                'scripts/CinnabarLabTradeRoom.asm',
                'scripts/CinnabarLabMetronomeRoom.asm',
                'scripts/CinnabarLabFossilRoom.asm',
                'scripts/CinnabarPokecenter.asm',
                'scripts/CinnabarMart.asm',
                'scripts/PokemonMansion1F.asm',
                'scripts/PokemonMansion2F.asm',
                'scripts/PokemonMansion3F.asm',
                'scripts/PokemonMansionB1F.asm',
                'scripts/CinnabarGym.asm',
                'scripts/ViridianGym.asm',
                'scripts/Route22.asm',
                'scripts/Route22Gate.asm',
                'scripts/Route23.asm',
                'scripts/VictoryRoad1F.asm',
                'scripts/VictoryRoad2F.asm',
                'scripts/VictoryRoad3F.asm',
                'scripts/HallOfFame.asm',
            }
            if (
                row['source_file'].startswith('data/pokemon/base_stats/') or
                row['source_file'].startswith('data/wild/') or
                row['source_file'].startswith('data/maps/headers/') or
                row['source_file'].startswith('data/maps/objects/') or
                (
                    row['source_file'].startswith('data/text/text_') and
                    row['source_file'].endswith('.asm')
                ) or
                row['source_file'].startswith('text/') or
                row['source_file'] in implemented_scripts or
                row['source_file'] in implemented_tables or
                row['source_file'].startswith('audio/') or
                row['source_file'] == 'data/maps/songs.asm'
            ):
                self.assertEqual(row['understanding'], 'documented')
                self.assertEqual(row['native_status'], 'ported')
                self.assertEqual(row['verification'], 'verified')
            else:
                self.assertEqual(row['understanding'], 'unknown')
                self.assertEqual(row['native_status'], 'not_started')
                self.assertEqual(row['verification'], 'unverified')

        self.assertEqual(len(rows), 1_862)
        self.assertEqual(len(domain_files), 30)
        self.assertEqual(total_spans, 121_241)
        self.assertEqual(total_bytes, 575_425)
        self.assertEqual(domain_files['species'], 151)
        self.assertEqual(domain_files['map_scripts'], 224)
        self.assertEqual(domain_files['map_text'], 211)
        self.assertEqual(domain_files['audio'], 385)

    def test_generated_content_profiles_are_complete_and_reproducible(self):
        native = POKEMON_RED_RE.parent / 'native-gb-pokemon-red'
        identity = native / 'src/generated/map_identity_profile.inc'
        layouts = native / 'src/generated/map_layout_profile.inc'
        text_resources = native / 'src/generated/text_resource_profile.inc'
        graphics_assets = native / 'src/generated/graphics_asset_profile.inc'
        compressed_pictures = (
            native / 'src/generated/compressed_picture_profile.inc'
        )
        palette_profile = native / 'src/generated/palette_profile.inc'
        text_tables = native / 'src/generated/map_text_table_profile.inc'
        text_entries = native / 'src/generated/map_text_entry_profile.inc'
        mart_inventories = native / 'src/generated/mart_inventory_profile.inc'
        celadon_vendors = (
            native / 'src/generated/celadon_vendor_profile.inc'
        )
        pc_profile = native / 'src/generated/pc_profile.inc'
        map_scripts = native / 'src/generated/map_script_profile.inc'
        script_tables = (
            native / 'src/generated/map_script_state_table_profile.inc'
        )
        script_entries = (
            native / 'src/generated/map_script_state_entry_profile.inc'
        )
        trainer_tables = (
            native / 'src/generated/map_trainer_table_profile.inc'
        )
        trainer_entries = (
            native / 'src/generated/map_trainer_entry_profile.inc'
        )
        save_states = native / 'src/generated/save_map_state_profile.inc'
        hidden_events = (
            native / 'src/generated/hidden_event_routine_profile.inc'
        )
        if (
            not identity.is_file() or not layouts.is_file() or
            not text_resources.is_file() or not graphics_assets.is_file() or
            not compressed_pictures.is_file() or not palette_profile.is_file() or
            not text_tables.is_file() or
            not text_entries.is_file() or not map_scripts.is_file() or
            not mart_inventories.is_file() or not celadon_vendors.is_file() or
            not pc_profile.is_file() or
            not script_tables.is_file() or not script_entries.is_file() or
            not trainer_tables.is_file() or not trainer_entries.is_file() or
            not save_states.is_file() or not hidden_events.is_file()
        ):
            self.skipTest('public Pokemon Red generated profiles are absent')

        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            generated_identity = temporary / 'identity.inc'
            generated_layouts = temporary / 'layouts.inc'
            generated_text = temporary / 'text.inc'
            generated_graphics = temporary / 'graphics.inc'
            generated_pictures = temporary / 'pictures.inc'
            generated_palettes = temporary / 'palettes.inc'
            generated_text_tables = temporary / 'text-tables.inc'
            generated_text_entries = temporary / 'text-entries.inc'
            generated_mart_inventories = temporary / 'mart-inventories.inc'
            generated_celadon_vendors = temporary / 'celadon-vendors.inc'
            generated_pc_profile = temporary / 'pc.inc'
            generated_map_scripts = temporary / 'map-scripts.inc'
            generated_script_tables = temporary / 'script-tables.inc'
            generated_script_entries = temporary / 'script-entries.inc'
            generated_trainer_tables = temporary / 'trainer-tables.inc'
            generated_trainer_entries = temporary / 'trainer-entries.inc'
            generated_save_states = temporary / 'save-states.inc'
            generated_hidden_events = temporary / 'hidden-events.inc'
            subprocess.run(
                [
                    sys.executable,
                    str(POKEMON_RED_RE / 'scripts/build-map-profile.py'),
                    '--reference', str(POKEMON_RED_RE / 'reference/pokered'),
                    '--source-map',
                    str(POKEMON_RED_RE / 'analysis/pokemon-red-ue-source-map.csv'),
                    '--identity-output', str(generated_identity),
                    '--layout-output', str(generated_layouts),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(generated_identity.read_bytes(), identity.read_bytes())
            self.assertEqual(generated_layouts.read_bytes(), layouts.read_bytes())
            subprocess.run(
                [
                    sys.executable,
                    str(POKEMON_RED_RE / 'scripts/build-text-profile.py'),
                    '--reference', str(POKEMON_RED_RE / 'reference/pokered'),
                    '--source-map',
                    str(POKEMON_RED_RE / 'analysis/pokemon-red-ue-source-map.csv'),
                    '--sym', str(POKEMON_RED_RE / 'reference/pokered/pokered.sym'),
                    '--output', str(generated_text),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(generated_text.read_bytes(), text_resources.read_bytes())
            subprocess.run(
                [
                    sys.executable,
                    str(POKEMON_RED_RE / 'scripts/build-graphics-profile.py'),
                    '--reference', str(POKEMON_RED_RE / 'reference/pokered'),
                    '--source-map',
                    str(POKEMON_RED_RE / 'analysis/pokemon-red-ue-source-map.csv'),
                    '--sym', str(POKEMON_RED_RE / 'reference/pokered/pokered.sym'),
                    '--rom', str(POKEMON_RED_RE / 'reference/pokered/pokered.gbc'),
                    '--output', str(generated_graphics),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                generated_graphics.read_bytes(), graphics_assets.read_bytes()
            )
            subprocess.run(
                [
                    sys.executable,
                    str(POKEMON_RED_RE / 'scripts/build-picture-profile.py'),
                    '--reference', str(POKEMON_RED_RE / 'reference/pokered'),
                    '--source-map',
                    str(POKEMON_RED_RE / 'analysis/pokemon-red-ue-source-map.csv'),
                    '--sym', str(POKEMON_RED_RE / 'reference/pokered/pokered.sym'),
                    '--rom', str(POKEMON_RED_RE / 'reference/pokered/pokered.gbc'),
                    '--output', str(generated_pictures),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                generated_pictures.read_bytes(), compressed_pictures.read_bytes()
            )
            subprocess.run(
                [
                    sys.executable,
                    str(POKEMON_RED_RE / 'scripts/build-palette-profile.py'),
                    '--reference', str(POKEMON_RED_RE / 'reference/pokered'),
                    '--sym', str(POKEMON_RED_RE / 'reference/pokered/pokered.sym'),
                    '--rom', str(POKEMON_RED_RE / 'reference/pokered/pokered.gbc'),
                    '--output', str(generated_palettes),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                generated_palettes.read_bytes(), palette_profile.read_bytes()
            )
            subprocess.run(
                [
                    sys.executable,
                    str(POKEMON_RED_RE / 'scripts/build-map-text-profile.py'),
                    '--reference', str(POKEMON_RED_RE / 'reference/pokered'),
                    '--sym', str(POKEMON_RED_RE / 'reference/pokered/pokered.sym'),
                    '--table-output', str(generated_text_tables),
                    '--entry-output', str(generated_text_entries),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                generated_text_tables.read_bytes(), text_tables.read_bytes()
            )
            self.assertEqual(
                generated_text_entries.read_bytes(), text_entries.read_bytes()
            )
            subprocess.run(
                [
                    sys.executable,
                    str(POKEMON_RED_RE / 'scripts/build-mart-profile.py'),
                    '--reference', str(POKEMON_RED_RE / 'reference/pokered'),
                    '--sym', str(POKEMON_RED_RE / 'reference/pokered/pokered.sym'),
                    '--output', str(generated_mart_inventories),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                generated_mart_inventories.read_bytes(),
                mart_inventories.read_bytes(),
            )
            subprocess.run(
                [
                    sys.executable,
                    str(
                        POKEMON_RED_RE /
                        'scripts/build-celadon-vendor-profile.py'
                    ),
                    '--reference', str(POKEMON_RED_RE / 'reference/pokered'),
                    '--sym', str(POKEMON_RED_RE / 'reference/pokered/pokered.sym'),
                    '--output', str(generated_celadon_vendors),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                generated_celadon_vendors.read_bytes(),
                celadon_vendors.read_bytes(),
            )
            subprocess.run(
                [
                    sys.executable,
                    str(POKEMON_RED_RE / 'scripts/build-pc-profile.py'),
                    '--reference', str(POKEMON_RED_RE / 'reference/pokered'),
                    '--sym', str(POKEMON_RED_RE / 'reference/pokered/pokered.sym'),
                    '--output', str(generated_pc_profile),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                generated_pc_profile.read_bytes(), pc_profile.read_bytes()
            )
            subprocess.run(
                [
                    sys.executable,
                    str(POKEMON_RED_RE / 'scripts/build-map-script-profile.py'),
                    '--reference', str(POKEMON_RED_RE / 'reference/pokered'),
                    '--sym', str(POKEMON_RED_RE / 'reference/pokered/pokered.sym'),
                    '--script-output', str(generated_map_scripts),
                    '--table-output', str(generated_script_tables),
                    '--entry-output', str(generated_script_entries),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                generated_map_scripts.read_bytes(), map_scripts.read_bytes()
            )
            self.assertEqual(
                generated_script_tables.read_bytes(), script_tables.read_bytes()
            )
            self.assertEqual(
                generated_script_entries.read_bytes(), script_entries.read_bytes()
            )
            subprocess.run(
                [
                    sys.executable,
                    str(POKEMON_RED_RE / 'scripts/build-map-trainer-profile.py'),
                    '--reference', str(POKEMON_RED_RE / 'reference/pokered'),
                    '--sym', str(POKEMON_RED_RE / 'reference/pokered/pokered.sym'),
                    '--table-output', str(generated_trainer_tables),
                    '--entry-output', str(generated_trainer_entries),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                generated_trainer_tables.read_bytes(), trainer_tables.read_bytes()
            )
            self.assertEqual(
                generated_trainer_entries.read_bytes(), trainer_entries.read_bytes()
            )
            subprocess.run(
                [
                    sys.executable,
                    str(POKEMON_RED_RE / 'scripts/build-save-profile.py'),
                    '--reference', str(POKEMON_RED_RE / 'reference/pokered'),
                    '--sym', str(POKEMON_RED_RE / 'reference/pokered/pokered.sym'),
                    '--output', str(generated_save_states),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                generated_save_states.read_bytes(), save_states.read_bytes()
            )
            subprocess.run(
                [
                    sys.executable,
                    str(
                        POKEMON_RED_RE /
                        'scripts/build-hidden-event-profile.py'
                    ),
                    '--reference', str(POKEMON_RED_RE / 'reference/pokered'),
                    '--sym',
                    str(POKEMON_RED_RE / 'reference/pokered/pokered.sym'),
                    '--output', str(generated_hidden_events),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                generated_hidden_events.read_bytes(), hidden_events.read_bytes()
            )

        self.assertEqual(identity.read_text().count('{"'), 248)
        self.assertEqual(layouts.read_text().count('{"'), 185)
        self.assertIn('UNUSED_MAP_F4', identity.read_text())
        self.assertIn('UnusedEmptyMap', layouts.read_text())
        self.assertEqual(text_resources.read_text().count('{"'), 2_444)
        self.assertIn('_PalletTownGirlText', text_resources.read_text())
        self.assertEqual(graphics_assets.read_text().count('{"'), 151)
        self.assertIn('PokemonLogoGraphics', graphics_assets.read_text())
        self.assertIn('gfx/tilesets/gym.2bpp', graphics_assets.read_text())
        self.assertEqual(compressed_pictures.read_text().count('{"'), 355)
        self.assertIn('MewPicFront', compressed_pictures.read_text())
        self.assertIn('gfx/trainers/lance.pic', compressed_pictures.read_text())
        self.assertEqual(text_tables.read_text().count('{"'), 223)
        self.assertEqual(text_entries.read_text().count('{"'), 1_210)
        self.assertIn('ViridianMartClerkSayHiToOakText', text_entries.read_text())
        self.assertEqual(mart_inventories.read_text().count('{"'), 16)
        self.assertIn('UnusedBikeShopClerkText', mart_inventories.read_text())
        self.assertEqual(celadon_vendors.read_text().count('{"'), 3)
        self.assertIn('PrizeMenuMon1Entries', celadon_vendors.read_text())
        self.assertIn('kVendingOfferCount = 3', celadon_vendors.read_text())
        self.assertEqual(pc_profile.read_text().count('{'), 18)
        self.assertIn('kHmMoveCount = 5', pc_profile.read_text())
        self.assertIn('DexRatingText_Own150To151', pc_profile.read_text())
        self.assertEqual(map_scripts.read_text().count('{"'), 223)
        self.assertEqual(script_tables.read_text().count('{"'), 98)
        self.assertEqual(script_entries.read_text().count('{"'), 381)
        self.assertIn('PalletTownOakHeyWaitScript', script_entries.read_text())
        self.assertEqual(trainer_tables.read_text().count('{"'), 68)
        self.assertEqual(trainer_entries.read_text().count('{0x'), 321)
        self.assertIn('Route3TrainerHeaders', trainer_tables.read_text())
        self.assertEqual(save_states.read_text().count('0x'), 248)
        self.assertEqual(save_states.read_text().count('0xFFFF'), 150)
        self.assertIn('PALLET_TOWN: wPalletTownCurScript', save_states.read_text())
        self.assertEqual(hidden_events.read_text().count('{'), 33)
        self.assertIn(
            'HiddenEventRoutineKind::OpenRedsPC',
            hidden_events.read_text(),
        )
        self.assertIn(
            'HiddenEventRoutineKind::StartSlotMachine',
            hidden_events.read_text(),
        )


if __name__ == '__main__':
    unittest.main()
