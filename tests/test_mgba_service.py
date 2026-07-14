#!/usr/bin/env python3

import json
import socket
import sys
import tempfile
import threading
import time
import unittest
from dataclasses import replace
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
NATIVE = REPO.parent / 'native-gb-tetris'
TETRIS_RE = REPO.parent / 'native-gb-tetris-re'
ROM = NATIVE / 'roms/Tetris (JUE) (V1.1) [!].gb'
SHA1 = '74591cc9501af93873f9a5d3eb12da12c0723bbc'
sys.path.insert(0, str(REPO / 'tools'))

from mgba_service import MgbaService, MgbaServiceError, rom_sha1  # noqa: E402
from scenario_live import LiveScenarioSession  # noqa: E402
from scenario_model import ScenarioFile, discover_scenarios, find_scenario  # noqa: E402


class FakeProcess:
    def __init__(self):
        self.returncode = None

    def poll(self):
        return self.returncode


class MgbaProtocolTest(unittest.TestCase):
    def service_pair(self, response):
        client, server = socket.socketpair()
        service = MgbaService(REPO, ROM, SHA1)
        service.process = FakeProcess()
        service.socket = client
        service.reader = client.makefile('r', encoding='utf-8', newline='\n')

        def reply():
            request = server.makefile('r', encoding='utf-8').readline()
            request_id, command, *_arguments = request.rstrip('\n').split('\t')
            result = response(int(request_id), command)
            server.sendall((json.dumps(result) + '\n').encode())
            server.close()

        thread = threading.Thread(target=reply)
        thread.start()
        return service, thread

    def close_pair(self, service, thread):
        service.reader.close()
        service.socket.close()
        thread.join()

    def test_command_protocol_checks_identity_and_errors(self):
        service, thread = self.service_pair(
            lambda request_id, command: {
                'id': request_id, 'ok': True, 'command': command, 'frame': 9,
            }
        )
        self.assertEqual(service.command('step', 1)['frame'], 9)
        self.close_pair(service, thread)

        service, thread = self.service_pair(
            lambda request_id, command: {
                'id': request_id, 'ok': False, 'command': command,
                'error': 'deliberate failure',
            }
        )
        with self.assertRaisesRegex(MgbaServiceError, 'deliberate failure'):
            service.command('observe')
        self.close_pair(service, thread)

    def test_detects_response_mismatch_and_process_failure(self):
        service, thread = self.service_pair(
            lambda request_id, command: {
                'id': request_id + 1, 'ok': True, 'command': command,
            }
        )
        with self.assertRaisesRegex(MgbaServiceError, 'did not match'):
            service.command('pause')
        self.close_pair(service, thread)

        service = MgbaService(REPO, ROM, SHA1)
        service.process = FakeProcess()
        service.process.returncode = 7
        with self.assertRaisesRegex(MgbaServiceError, 'status 7'):
            service.command('observe')

    def test_rom_hash_is_streamed_and_checked(self):
        if not ROM.is_file():
            self.skipTest('local ignored Tetris v1.1 ROM is absent')
        self.assertEqual(rom_sha1(ROM), SHA1)
        service = MgbaService(REPO, ROM, '0' * 40)
        with self.assertRaisesRegex(MgbaServiceError, 'does not match'):
            service.start()

    def test_live_session_can_preserve_game_specific_observations(self):
        class FakeService:
            def observe(self):
                return {
                    'schema': 'gbre.observation.v1',
                    'side': 'original',
                    'clock': {'emulator_frame': 17},
                    'flow': {'phase': 'Playing'},
                    'player': {'world_x': 42},
                }

        live = LiveScenarioSession(
            FakeService(), passthrough_observation=True,
        )
        observation = live.observe()
        self.assertEqual(observation['flow']['phase'], 'Playing')
        self.assertEqual(observation['player']['world_x'], 42)
        self.assertEqual(observation['events'], [])


class MgbaLiveIntegrationTest(unittest.TestCase):
    def test_live_pause_step_patch_framebuffer_and_state(self):
        executable = REPO / '.cache/mgba/build-headless/mgba-headless'
        if not ROM.is_file() or not executable.is_file():
            self.skipTest('ignored ROM or pinned mGBA build is absent')
        with tempfile.TemporaryDirectory() as temporary:
            service = MgbaService(
                REPO, ROM, SHA1, runtime_root=Path(temporary), timeout=8,
            )
            with service:
                initial = service.observe()['clock']['emulator_frame']
                service.run()
                time.sleep(0.02)
                running_frame = service.pause()['frame']
                self.assertGreater(running_frame, initial)
                time.sleep(0.01)
                self.assertEqual(
                    service.observe()['clock']['emulator_frame'], running_frame,
                )
                service.step(3)
                self.assertEqual(
                    service.observe()['clock']['emulator_frame'], running_frame + 3,
                )
                service.write(0xC000, 123)
                self.assertEqual(service.read(0xC000), [123])
                capture = service.capture()
                self.assertGreater(capture.stat().st_size, 100)
                raw_capture = service.capture_raw()
                self.assertEqual(raw_capture.stat().st_size, 160 * 144 * 4)

                state = Path(temporary) / 'state.ss0'
                service.save_state(state, 'test.live')
                saved_frame = service.observe()['clock']['emulator_frame']
                service.step(2)
                service.load_state(state, 'test.live')
                self.assertEqual(
                    service.observe()['clock']['emulator_frame'], saved_frame,
                )
                metadata = json.loads(
                    state.with_suffix('.ss0.gbre.json').read_text()
                )
                self.assertEqual(metadata['scenario_id'], 'test.live')

    def test_live_scenario_schedule_landmark_and_patch(self):
        executable = REPO / '.cache/mgba/build-headless/mgba-headless'
        if not ROM.is_file() or not executable.is_file():
            self.skipTest('ignored ROM or pinned mGBA build is absent')
        scenarios = discover_scenarios(TETRIS_RE / 'scenarios')
        with tempfile.TemporaryDirectory() as temporary:
            service = MgbaService(
                REPO, ROM, SHA1, runtime_root=Path(temporary), timeout=8,
            )
            with service:
                live = LiveScenarioSession(service)
                startup = find_scenario(scenarios, 'tetris.start-type-a')
                live.load(startup)
                landmark = startup.landmarks[0]
                observation = live.advance_landmark(
                    landmark.condition, landmark.timeout,
                )
                self.assertEqual(observation['screen'], 'GameTypeMenu')

                rocket = find_scenario(scenarios, 'tetris.rocket-large')
                live.load(rocket)
                live.step(700)
                self.assertEqual(service.read(0xC0A2), [0x20])
                self.assertEqual(service.read(0xFFE1), [0x0D])

    def test_live_event_inputs_advance_and_timeout(self):
        executable = REPO / '.cache/mgba/build-headless/mgba-headless'
        if not ROM.is_file() or not executable.is_file():
            self.skipTest('ignored ROM or pinned mGBA build is absent')
        source = find_scenario(
            discover_scenarios(TETRIS_RE / 'scenarios'), 'tetris.start-type-a',
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            events = root / 'events.csv'
            events.write_text(
                'action,keys,condition,timeout\n'
                'wait,,clock.emulator_frame >= 3,5\n'
                'tap,A,,2\n'
            )
            scenario = replace(
                source,
                original=replace(
                    source.original,
                    input=ScenarioFile(events, 'event'),
                ),
            )
            service = MgbaService(REPO, ROM, SHA1, runtime_root=root, timeout=8)
            with service:
                live = LiveScenarioSession(service)
                live.load(scenario)
                reached = live.advance_next_event()
                self.assertEqual(reached['clock']['emulator_frame'], 3)
                tapped = live.advance_next_event()
                self.assertEqual(tapped['clock']['emulator_frame'], 4)
                self.assertEqual(service.observe()['input']['mask'], 0)

                timeout_events = root / 'timeout.csv'
                timeout_events.write_text(
                    'action,keys,condition,timeout\n'
                    'wait,,clock.emulator_frame >= 999,2\n'
                )
                timeout_scenario = replace(
                    scenario,
                    original=replace(
                        scenario.original,
                        input=ScenarioFile(timeout_events, 'event'),
                    ),
                )
                live.load(timeout_scenario)
                with self.assertRaisesRegex(MgbaServiceError, 'not reached'):
                    live.advance_next_event()


if __name__ == '__main__':
    unittest.main()
