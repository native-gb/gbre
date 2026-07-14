#!/usr/bin/env python3

import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))

from build_rgbds_source_map import (  # noqa: E402
    Marker,
    MarkerDefinition,
    instrument_source,
    make_spans,
    marker_line,
    parse_marker_symbols,
    verify_coverage,
)
from gbre_common import (  # noqa: E402
    Section,
    linear_rom_address,
    read_rgbds_sections,
    read_rgbds_symbols,
)


class RgbdsBankMappingTest(unittest.TestCase):
    def test_cpu_addresses_become_linear_rom_offsets(self):
        self.assertEqual(linear_rom_address(0, 0x0150, 0x10000), 0x0150)
        self.assertEqual(linear_rom_address(0, 0x7FFF, 0x8000), 0x7FFF)
        self.assertEqual(linear_rom_address(1, 0x4000, 0x10000), 0x4000)
        self.assertEqual(linear_rom_address(2, 0x6002, 0x10000), 0xA002)
        self.assertEqual(linear_rom_address(3, 0x7FFF, 0x10000), 0xFFFF)
        with self.assertRaises(ValueError):
            linear_rom_address(2, 0x2000, 0x10000)
        with self.assertRaises(ValueError):
            linear_rom_address(4, 0x4000, 0x10000)

    def test_legacy_and_modern_map_headings_preserve_rom_banks(self):
        map_text = '''ROM0 bank #0 (HOME):
  SECTION: $0100-$0103 ($0004 bytes) ["Entry point"]
WRAM0 bank #0:
  SECTION: $C000-$C00F ($0010 bytes) ["Work RAM"]
ROM Bank #2:
  SECTION: $6002-$6072 ($0071 bytes) ["level enemies"]
ROMX bank #3:
  SECTION: $4000-$4002 ($0003 bytes) ["bank 3"]
'''
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'test.map'
            path.write_text(map_text)
            sections = read_rgbds_sections(path, 0x10000)

        self.assertEqual(
            sections,
            [
                Section(0x0100, 0x0104, 'Entry point', 0),
                Section(0xA002, 0xA073, 'level enemies', 2),
                Section(0xC000, 0xC003, 'bank 3', 3),
            ],
        )

    def test_symbols_from_romx_banks_use_linear_offsets(self):
        symbol_text = '''00:0150 Start
02:6002 level_1_1_enemies
03:7FFF LastByte
00:C000 NotARomSymbol
'''
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'test.sym'
            path.write_text(symbol_text)
            symbols = read_rgbds_symbols(path, 0x10000)

        self.assertEqual(symbols[0x0150], ['Start'])
        self.assertEqual(symbols[0xA002], ['level_1_1_enemies'])
        self.assertEqual(symbols[0xFFFF], ['LastByte'])
        self.assertNotIn(0xC000, symbols)

    def test_marker_bank_disambiguates_equal_cpu_addresses(self):
        sections = [
            Section(0x4000, 0x4004, 'shared name', 1),
            Section(0x8000, 0x8004, 'shared name', 2),
        ]
        markers = [
            Marker(0x4000, 1, 'bank1.asm', 1, 'shared name', 'db 1, 2, 3, 4'),
            Marker(0x8000, 2, 'bank2.asm', 1, 'shared name', 'db 5, 6, 7, 8'),
        ]
        spans = make_spans(markers, sections)
        verify_coverage(spans, sections)

        self.assertEqual([(span.start, span.end) for span in spans], [
            (0x4000, 0x4004),
            (0x8000, 0x8004),
        ])
        self.assertEqual([span.bank for span in spans], [1, 2])

    def test_last_source_marker_at_an_address_owns_emitted_bytes(self):
        section = Section(0x4000, 0x4002, 'bank 1', 1)
        markers = [
            Marker(0x4000, 1, 'bank1.asm', 3, 'bank 1', 'Label::', 10),
            Marker(0x4000, 1, 'bank1.asm', 4, 'bank 1', 'dw $1234', 11),
        ]
        spans = make_spans(markers, [section])
        self.assertEqual(spans[0].source_line, 4)
        self.assertEqual(spans[0].source_text, 'dw $1234')

    def test_instrumentation_and_parser_record_bank_and_cpu_address(self):
        self.assertEqual(marker_line(7), '.GBRE_00000007::\n')
        self.assertEqual(marker_line(7, section_root=True), 'GBRE_ROOT_00000007::\n')

        with tempfile.TemporaryDirectory() as temporary:
            symbol_path = Path(temporary) / 'test.sym'
            symbol_path.write_text('02:6002 level.GBRE_00000007\n')
            definitions = {
                7: MarkerDefinition(7, 2, 'bank2.asm', 1, 'bank 2', 'db $00')
            }
            markers = parse_marker_symbols(
                symbol_path,
                definitions,
                0x10000,
            )

        self.assertEqual(markers[0].bank, 2)
        self.assertEqual(markers[0].address, 0xA002)

    def test_instrumentation_recognizes_legacy_romx_section_syntax(self):
        with tempfile.TemporaryDirectory() as temporary:
            source_path = Path(temporary) / 'bank2.asm'
            source_path.write_text(
                'SECTION "bank 2", ROMX, BANK[2]\nData::\n\tdb $42\n'
            )
            definitions = {}
            instrument_source(source_path, 'bank2.asm', definitions, 0)
            instrumented = source_path.read_text()

        self.assertIn('GBRE_ROOT_00000000::', instrumented)
        self.assertIn('.GBRE_00000002::', instrumented)
        self.assertEqual({item.bank for item in definitions.values()}, {2})


if __name__ == '__main__':
    unittest.main()
