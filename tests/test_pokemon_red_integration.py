#!/usr/bin/env python3

import csv
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
POKEMON_RED_RE = REPO.parent / 'native-gb-pokemon-red-re'
sys.path.insert(0, str(REPO / 'tools'))

from gbre_common import load_manifest  # noqa: E402


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
                'pokemon_red.rgbfix_padding',
            ],
        )

    def test_native_anchors_exist_and_are_unique(self):
        root = self.manifest.path.parent.parent
        for unit in self.manifest.units:
            for target in unit.native:
                text = (root / target.path).resolve().read_text()
                self.assertEqual(text.count(target.anchor), 1, unit.id)

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
        path = POKEMON_RED_RE / 'analysis/pokemon-red-ue-rom-map.csv'
        if not path.is_file():
            self.skipTest('generated Pokemon Red ROM map is absent')

        cursor = 0
        status_bytes = Counter()
        padding_sections = Counter()
        last_emitted_row = None
        with path.open(newline='') as source:
            for row in csv.DictReader(source):
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
        self.assertEqual(status_bytes['documented'], 1_548)
        self.assertEqual(status_bytes['excluded'], 311_296)
        self.assertEqual(status_bytes['verified'], 245_851)
        self.assertEqual(status_bytes['unknown'], 489_881)
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
                'data/trainers/move_choices.asm',
                'data/trainers/names.asm',
                'data/trainers/parties.asm',
                'data/trainers/pic_pointers_money.asm',
                'data/tilesets/collision_tile_ids.asm',
                'data/tilesets/bike_riding_tilesets.asm',
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
                'engine/events/prize_menu.asm',
                'engine/events/set_blackout_map.asm',
                'engine/events/card_key.asm',
                'engine/events/cinnabar_lab.asm',
                'data/events/card_key_maps.asm',
                'data/events/hidden_coins.asm',
                'engine/events/vending_machine.asm',
                'engine/events/hidden_items.asm',
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
                'scripts/PalletTown.asm',
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
                row['source_file'] in implemented_tables
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
        text_tables = native / 'src/generated/map_text_table_profile.inc'
        text_entries = native / 'src/generated/map_text_entry_profile.inc'
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
        if (
            not identity.is_file() or not layouts.is_file() or
            not text_resources.is_file() or not text_tables.is_file() or
            not text_entries.is_file() or not map_scripts.is_file() or
            not script_tables.is_file() or not script_entries.is_file() or
            not trainer_tables.is_file() or not trainer_entries.is_file() or
            not save_states.is_file()
        ):
            self.skipTest('public Pokemon Red generated profiles are absent')

        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            generated_identity = temporary / 'identity.inc'
            generated_layouts = temporary / 'layouts.inc'
            generated_text = temporary / 'text.inc'
            generated_text_tables = temporary / 'text-tables.inc'
            generated_text_entries = temporary / 'text-entries.inc'
            generated_map_scripts = temporary / 'map-scripts.inc'
            generated_script_tables = temporary / 'script-tables.inc'
            generated_script_entries = temporary / 'script-entries.inc'
            generated_trainer_tables = temporary / 'trainer-tables.inc'
            generated_trainer_entries = temporary / 'trainer-entries.inc'
            generated_save_states = temporary / 'save-states.inc'
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

        self.assertEqual(identity.read_text().count('{"'), 248)
        self.assertEqual(layouts.read_text().count('{"'), 185)
        self.assertIn('UNUSED_MAP_F4', identity.read_text())
        self.assertIn('UnusedEmptyMap', layouts.read_text())
        self.assertEqual(text_resources.read_text().count('{"'), 2_444)
        self.assertIn('_PalletTownGirlText', text_resources.read_text())
        self.assertEqual(text_tables.read_text().count('{"'), 223)
        self.assertEqual(text_entries.read_text().count('{"'), 1_210)
        self.assertIn('ViridianMartClerkSayHiToOakText', text_entries.read_text())
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


if __name__ == '__main__':
    unittest.main()
