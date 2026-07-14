#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mgba_service import MgbaService
from scenario_live import LiveScenarioSession
from scenario_model import discover_scenarios, find_scenario
from scenario_runner import ScenarioRunner, promote_temporary


DEFAULT_GBRE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_NATIVE_ROOT = DEFAULT_GBRE_ROOT.parent / 'native-gb-tetris'
DEFAULT_SCENARIO_ROOT = DEFAULT_GBRE_ROOT.parent / 'native-gb-tetris-re/scenarios'


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run and inspect GBRE scenarios')
    parser.add_argument('--root', type=Path, default=DEFAULT_SCENARIO_ROOT)
    parser.add_argument('--native-root', type=Path, default=DEFAULT_NATIVE_ROOT)
    parser.add_argument('--output-root', type=Path)
    parser.add_argument('--include-temporary', action='store_true')
    subparsers = parser.add_subparsers(dest='command', required=True)

    listing = subparsers.add_parser('list')
    listing.add_argument('--filter', default='')

    subparsers.add_parser('validate')

    for command in ('run-original', 'run-native', 'compare', 'run'):
        action = subparsers.add_parser(command)
        action.add_argument('scenario')
        if command != 'compare':
            action.add_argument('--rom', type=Path, required=True)

    live = subparsers.add_parser('live-original')
    live.add_argument('scenario')
    live.add_argument('--rom', type=Path, required=True)
    live.add_argument('--frames', type=int)
    live.add_argument('--capture', action='store_true')

    landmark = subparsers.add_parser('live-landmark')
    landmark.add_argument('scenario')
    landmark.add_argument('landmark')
    landmark.add_argument('--rom', type=Path, required=True)

    run_all = subparsers.add_parser('run-all')
    run_all.add_argument('--rom', type=Path, required=True)
    run_all.add_argument('--tag')

    promote = subparsers.add_parser('promote')
    promote.add_argument('temporary', type=Path)
    promote.add_argument('--destination', type=Path, default=DEFAULT_SCENARIO_ROOT / 'curated')
    return parser


def print_scenario(scenario) -> None:
    parameters = ', '.join(f'{name}={value}' for name, value in scenario.parameter_values)
    suffix = f' [{parameters}]' if parameters else ''
    print(f'{scenario.id:<36} {scenario.kind:<13} {scenario.title}{suffix}')
    if scenario.description:
        print(f'  {scenario.description}')
    if scenario.tags or scenario.subsystems:
        print(f'  tags={",".join(scenario.tags)} systems={",".join(scenario.subsystems)}')


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()
    try:
        if args.command == 'promote':
            print(promote_temporary(args.temporary, args.destination))
            return 0
        scenarios = discover_scenarios(args.root, allow_temporary=args.include_temporary)
        if args.command == 'list':
            needle = args.filter.lower()
            for scenario in scenarios:
                haystack = ' '.join((scenario.id, scenario.title, scenario.description,
                                     *scenario.tags, *scenario.subsystems)).lower()
                if not needle or needle in haystack:
                    print_scenario(scenario)
            return 0
        if args.command == 'validate':
            print(f'VALID: {len(scenarios)} expanded scenarios')
            return 0
        runner = ScenarioRunner(DEFAULT_GBRE_ROOT, args.native_root, args.output_root)
        if args.command == 'run-all':
            selected = [scenario for scenario in scenarios
                        if not args.tag or args.tag in scenario.tags]
            for scenario in selected:
                print(f'RUN {scenario.id}', flush=True)
                result = runner.run_and_compare(scenario, args.rom)
                print(result.output, end='')
                if result.returncode != 0:
                    return result.returncode
            print(f'MATCH: {len(selected)} scenarios passed')
            return 0
        scenario = find_scenario(scenarios, args.scenario)
        if args.command in {'live-original', 'live-landmark'}:
            service = MgbaService(DEFAULT_GBRE_ROOT, args.rom, scenario.rom_sha1)
            with service:
                live = LiveScenarioSession(service)
                observation = live.load(scenario)
                if args.command == 'live-original':
                    frames = scenario.frames if args.frames is None else args.frames
                    if frames < 0:
                        raise ValueError('--frames must not be negative')
                    if frames:
                        observation = live.step(frames)
                    if args.capture:
                        print(f'framebuffer={service.capture()}')
                else:
                    landmark = next((item for item in scenario.landmarks
                                     if item.id == args.landmark), None)
                    if landmark is None:
                        raise ValueError(f'unknown landmark {args.landmark!r}')
                    observation = live.advance_landmark(
                        landmark.condition, landmark.timeout,
                    )
                print(json.dumps(observation, indent=2))
            return 0
        if args.command == 'run-original':
            result = runner.run_original(scenario, args.rom)
        elif args.command == 'run-native':
            result = runner.run_native(scenario, args.rom)
        elif args.command == 'compare':
            result = runner.compare(scenario)
        else:
            result = runner.run_and_compare(scenario, args.rom)
        print(result.output, end='')
        return result.returncode
    except (OSError, RuntimeError, ValueError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
