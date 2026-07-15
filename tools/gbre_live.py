#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from mgba_service import MgbaService
from scenario_live import LiveScenarioSession
from scenario_capture import capture_temporary
from scenario_inputs import load_event_inputs, load_strict_inputs
from scenario_model import discover_scenarios, find_scenario
from scenario_runner import promote_temporary


def scenario_json(scenario) -> dict[str, Any]:
    native_inputs: list[dict[str, Any]] = []
    if scenario.native.input is not None:
        if scenario.native.input.mode == 'strict':
            native_inputs = [
                {'tick': item.tick, 'keys': list(item.keys)}
                for item in load_strict_inputs(scenario.native.input.path)
            ]
        else:
            native_inputs = [
                {
                    'action': item.action, 'keys': list(item.keys),
                    'condition': item.condition, 'timeout': item.timeout,
                }
                for item in load_event_inputs(scenario.native.input.path)
            ]
    return {
        'id': scenario.id,
        'title': scenario.title,
        'description': scenario.description,
        'kind': scenario.kind,
        'tags': list(scenario.tags),
        'subsystems': list(scenario.subsystems),
        'frames': scenario.frames,
        'comparison_profile': scenario.comparison_profile,
        'trace_landmark': scenario.trace_landmark,
        'trace_frames': scenario.trace_frames,
        'fields': [field.__dict__ for field in scenario.fields],
        'landmarks': [landmark.__dict__ for landmark in scenario.landmarks],
        'native_setup': str(scenario.native.setup) if scenario.native.setup else '',
        'native_input': str(scenario.native.input.path) if scenario.native.input else '',
        'native_input_mode': scenario.native.input.mode if scenario.native.input else '',
        'native_inputs': native_inputs,
        'parameters': dict(scenario.parameter_values),
    }


class Coordinator:
    def __init__(self, gbre_root: Path, scenario_root: Path, rom: Path,
                 adapter: Path | None = None,
                 passthrough_observation: bool = False):
        self.gbre_root = gbre_root.resolve()
        self.scenarios = discover_scenarios(scenario_root)
        self.rom = rom.resolve()
        self.scenario_root = scenario_root.resolve()
        self.adapter = adapter.resolve() if adapter is not None else None
        self.passthrough_observation = passthrough_observation
        self.service: MgbaService | None = None
        self.live: LiveScenarioSession | None = None
        self.current_scenario = None
        self.current_has_original = False

    def start_original(self, sha1: str) -> None:
        if self.service is not None:
            return
        self.service = MgbaService(
            self.gbre_root, self.rom, sha1, adapter=self.adapter,
        )
        self.service.start()
        self.live = LiveScenarioSession(
            self.service,
            passthrough_observation=self.passthrough_observation,
        )

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        command = request.get('command')
        if command == 'list':
            query = str(request.get('query', '')).lower()
            items = [scenario_json(item) for item in self.scenarios]
            if query:
                items = [item for item in items if query in json.dumps(item).lower()]
            return {'scenarios': items}
        if command == 'load':
            scenario = find_scenario(self.scenarios, str(request['id']))
            self.current_scenario = scenario
            self.current_has_original = bool(request.get('original', True))
            result = {'scenario': scenario_json(scenario)}
            if self.current_has_original:
                self.start_original(scenario.rom_sha1)
                assert self.live is not None
                result['original'] = self.live.load(scenario)
            return result
        if command == 'capture-temporary':
            if self.current_scenario is None:
                raise ValueError('load a scenario first')
            native = dict(request['native'])
            original = (self.live.observe()
                        if self.live is not None and self.current_has_original else None)
            path = capture_temporary(
                self.scenario_root, self.current_scenario, native, original,
                self.service if self.current_has_original else None,
                self.live.recorded_inputs if self.live is not None else None,
            )
            return {'path': str(path)}
        if command == 'promote-temporary':
            source = Path(str(request['path']))
            destination = promote_temporary(
                source, self.scenario_root / 'curated',
            )
            return {'path': str(destination)}
        live = self._require_live()
        if command == 'reset-original':
            return {'original': live.reset()}
        if command == 'step-original':
            return {'original': live.step(int(request.get('frames', 1)))}
        if command == 'input-original':
            return {'original': live.set_keys(int(request.get('mask', 0)))}
        if command == 'observe-original':
            return {'original': live.observe()}
        if command == 'capture-original':
            assert self.service is not None
            return {'path': str(self.service.capture(str(request.get('name', 'original.png'))))}
        if command == 'capture-original-raw':
            assert self.service is not None
            return {
                'path': str(self.service.capture_raw(
                    str(request.get('name', 'original.rgba')),
                )),
                'width': 160,
                'height': 144,
                'format': 'rgba32',
            }
        if command == 'advance-landmark':
            scenario = live._require_scenario()
            landmark_id = str(request['id'])
            landmark = next((item for item in scenario.landmarks
                             if item.id == landmark_id), None)
            if landmark is None:
                raise ValueError(f'unknown landmark {landmark_id!r}')
            return {'original': live.advance_landmark(
                landmark.condition, landmark.timeout,
            )}
        if command == 'advance-event':
            return {'original': live.advance_next_event()}
        if command == 'compare':
            result = live.compare(dict(request['native']))
            return {
                'matches': result.matches,
                'differences': [difference.__dict__ for difference in result.differences],
                'original': live.last_original,
            }
        if command == 'shutdown':
            return {'shutdown': True}
        raise ValueError(f'unknown coordinator command {command!r}')

    def _require_live(self) -> LiveScenarioSession:
        if self.live is None:
            raise ValueError('load a scenario first')
        return self.live

    def close(self) -> None:
        if self.service is not None:
            self.service.stop()


def serve(coordinator: Coordinator) -> int:
    try:
        for line in sys.stdin:
            try:
                request = json.loads(line)
                result = coordinator.handle(request)
                response = {'ok': True, **result}
            except Exception as error:  # Process boundary returns actionable errors.
                response = {'ok': False, 'error': str(error)}
            print(json.dumps(response, separators=(',', ':')), flush=True)
            if response.get('shutdown'):
                return 0
        return 0
    finally:
        coordinator.close()


def main() -> int:
    parser = argparse.ArgumentParser(description='Live GBRE scenario coordinator.')
    parser.add_argument('--gbre-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--scenario-root', type=Path, required=True)
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--adapter', type=Path)
    parser.add_argument('--passthrough-observation', action='store_true')
    parser.add_argument('--stdio', action='store_true', required=True)
    arguments = parser.parse_args()
    return serve(Coordinator(
        arguments.gbre_root, arguments.scenario_root, arguments.rom,
        adapter=arguments.adapter,
        passthrough_observation=arguments.passthrough_observation,
    ))


if __name__ == '__main__':
    raise SystemExit(main())
