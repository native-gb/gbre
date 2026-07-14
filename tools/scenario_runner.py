#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from scenario_inputs import load_event_inputs, load_strict_inputs
from scenario_model import Scenario


@dataclass(frozen=True)
class ScenarioPaths:
    directory: Path
    original_trace: Path
    native_trace: Path
    result: Path


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    output: str


class ScenarioRunner:
    def __init__(self, gbre_root: Path, native_root: Path, output_root: Path | None = None):
        self.gbre_root = gbre_root.resolve()
        self.native_root = native_root.resolve()
        self.output_root = (output_root or self.gbre_root / 'build/scenarios').resolve()

    def paths(self, scenario: Scenario) -> ScenarioPaths:
        directory = self.output_root / scenario.id
        return ScenarioPaths(
            directory=directory,
            original_trace=directory / 'original.jsonl',
            native_trace=directory / 'native.jsonl',
            result=directory / 'result.txt',
        )

    def validate_runtime(self, scenario: Scenario, rom: Path) -> None:
        if not rom.is_file():
            raise ValueError(f'ROM does not exist: {rom}')
        digest = hashlib.sha1(rom.read_bytes()).hexdigest()
        if digest != scenario.rom_sha1:
            raise ValueError(
                f'{scenario.id}: ROM SHA-1 {digest} does not match {scenario.rom_sha1}'
            )
        for side in (scenario.original, scenario.native):
            if side.input:
                if side.input.mode == 'strict':
                    load_strict_inputs(side.input.path)
                else:
                    load_event_inputs(side.input.path)

    def _run(self, command: list[str], *, write_to: Path | None = None) -> CommandResult:
        completed = subprocess.run(
            command, cwd=self.gbre_root, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        output = completed.stdout
        if write_to is not None:
            write_to.parent.mkdir(parents=True, exist_ok=True)
            write_to.write_text(output)
        return CommandResult(tuple(command), completed.returncode, output)

    def run_original(self, scenario: Scenario, rom: Path) -> CommandResult:
        self.validate_runtime(scenario, rom)
        if scenario.original.input is None:
            raise ValueError(f'{scenario.id}: original input is not configured')
        if scenario.original.input.mode != 'strict':
            raise ValueError(
                f'{scenario.id}: event input requires the live coordinator, not batch trace'
            )
        paths = self.paths(scenario)
        paths.directory.mkdir(parents=True, exist_ok=True)
        command = [
            str(self.gbre_root / 'scripts/run-tetris-oracle.sh'),
            str(rom.resolve()), str(scenario.original.input.path),
            str(paths.original_trace), str(scenario.frames),
        ]
        if scenario.original.patches:
            command.append(str(scenario.original.patches))
        elif scenario.parameter_values:
            command.append('')
        parameters = scenario.parameter_map
        if 'song_id' in parameters:
            if not scenario.original.patches:
                raise ValueError(f'{scenario.id}: music parameter requires original patches')
            command.append(str(parameters['song_id']))
        return self._run(command)

    def run_native(self, scenario: Scenario, rom: Path) -> CommandResult:
        self.validate_runtime(scenario, rom)
        paths = self.paths(scenario)
        paths.directory.mkdir(parents=True, exist_ok=True)
        parameters = scenario.parameter_map
        if 'song_id' in parameters:
            command = [
                str(self.native_root / 'build-debug/native-gb-tetris-music-trace'),
                '--rom', str(rom.resolve()), '--output', str(paths.native_trace),
                '--song', str(int(parameters['song_id']) - 1),
                '--frames', str(scenario.frames - 700),
            ]
            return self._run(command)
        if scenario.native.input is None:
            raise ValueError(f'{scenario.id}: native input is not configured')
        if scenario.native.input.mode != 'strict':
            raise ValueError(
                f'{scenario.id}: event input requires the live coordinator, not batch trace'
            )
        command = [
            str(self.native_root / 'build-debug/native-gb-tetris-trace'),
            '--rom', str(rom.resolve()), '--input', str(scenario.native.input.path),
            '--output', str(paths.native_trace), '--frames', str(scenario.frames),
        ]
        if scenario.native.setup:
            command.extend(('--setup', str(scenario.native.setup)))
        return self._run(command)

    def _comparison_commands(self, scenario: Scenario, paths: ScenarioPaths) -> list[list[str]]:
        python = 'python3'
        common = ['--original', str(paths.original_trace), '--native', str(paths.native_trace)]
        tools = self.gbre_root / 'tools'
        profile = scenario.comparison_profile
        if profile == 'transitions':
            return [[python, str(tools / 'compare_tetris_traces.py'), *common]]
        if profile == 'menus':
            return [
                [python, str(tools / 'compare_tetris_traces.py'), *common],
                [python, str(tools / 'compare_tetris_menus.py'), *common],
            ]
        if profile == 'controls':
            return [[python, str(tools / 'compare_tetris_controls.py'), *common]]
        if profile == 'attract':
            return [[python, str(tools / 'compare_tetris_attract.py'), *common]]
        if profile in {'rocket-large', 'buran-height-five'}:
            return [[
                python, str(tools / 'compare_tetris_endings.py'), *common,
                '--scenario', profile,
            ]]
        if profile == 'music':
            song_id = scenario.parameter_map.get('song_id')
            if song_id is None:
                raise ValueError(f'{scenario.id}: music comparison requires song_id')
            return [[
                python, str(tools / 'compare_tetris_music.py'), *common,
                '--song-id', str(song_id),
            ]]
        if profile == 'fields':
            raise ValueError(
                f'{scenario.id}: field comparison requires live normalized observations'
            )
        raise ValueError(f'{scenario.id}: unknown comparison profile {profile!r}')

    def compare(self, scenario: Scenario) -> CommandResult:
        paths = self.paths(scenario)
        if not paths.original_trace.is_file() or not paths.native_trace.is_file():
            raise ValueError(f'{scenario.id}: run original and native before compare')
        commands = self._comparison_commands(scenario, paths)
        outputs = []
        first_failure = 0
        for command in commands:
            result = self._run(command)
            outputs.append(result.output)
            if result.returncode != 0 and first_failure == 0:
                first_failure = result.returncode
        output = ''.join(outputs)
        paths.result.write_text(output)
        return CommandResult(tuple(item for command in commands for item in command),
                             first_failure, output)

    def run_and_compare(self, scenario: Scenario, rom: Path) -> CommandResult:
        original = self.run_original(scenario, rom)
        if original.returncode != 0:
            return original
        native = self.run_native(scenario, rom)
        if native.returncode != 0:
            return native
        return self.compare(scenario)


def promote_temporary(source: Path, destination_root: Path) -> Path:
    source = source.resolve()
    manifest = source / 'scenario.toml'
    if not manifest.is_file():
        raise ValueError(f'temporary capture has no scenario.toml: {source}')
    text = manifest.read_text()
    if re_kind := next((line for line in text.splitlines()
                        if line.strip().startswith('kind =')), None):
        if 'temporary' not in re_kind:
            raise ValueError(f'{source}: scenario is not temporary')
    else:
        raise ValueError(f'{source}: scenario has no kind')
    identifier = next((line.split('=', 1)[1].strip().strip('"')
                       for line in text.splitlines() if line.strip().startswith('id =')), '')
    if not identifier:
        raise ValueError(f'{source}: scenario has no id')
    destination = destination_root.resolve() / identifier
    if destination.exists():
        raise ValueError(f'curated destination already exists: {destination}')
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns(
        'native-cache.bin', '*.png', '*.jsonl', '*.ss0', '*.ss0.gbre.json',
        '*-observation.json', '__pycache__'
    ))
    promoted = (destination / 'scenario.toml').read_text().replace(
        'kind = "temporary"', 'kind = "curated"', 1
    )
    promoted = '\n'.join(
        line for line in promoted.splitlines()
        if not line.strip().startswith('save_state =')
    ) + '\n'
    (destination / 'scenario.toml').write_text(promoted)
    return destination
