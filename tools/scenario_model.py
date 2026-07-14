#!/usr/bin/env python3

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


SCENARIO_KINDS = {'curated', 'parameterized', 'temporary'}
COMPARISON_POLICIES = {
    'exact', 'ordered', 'tolerance', 'transform', 'ignore',
    'intentional_difference',
}
INPUT_MODES = {'strict', 'event'}
IDENTIFIER_RE = re.compile(r'^[a-z0-9][a-z0-9._-]*$')
TEMPLATE_RE = re.compile(r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}')


@dataclass(frozen=True)
class ScenarioFile:
    path: Path
    mode: str


@dataclass(frozen=True)
class ScenarioSide:
    input: ScenarioFile | None
    patches: Path | None
    setup: Path | None
    save_state: Path | None
    adapter: str


@dataclass(frozen=True)
class ComparisonField:
    path: str
    policy: str
    tolerance: float
    transform: str
    note: str


@dataclass(frozen=True)
class Landmark:
    id: str
    condition: str
    side: str
    timeout: int
    presentation: bool


@dataclass(frozen=True)
class Parameter:
    name: str
    values: tuple[Any, ...]


@dataclass(frozen=True)
class Scenario:
    path: Path
    schema_version: int
    id: str
    title: str
    description: str
    kind: str
    tags: tuple[str, ...]
    subsystems: tuple[str, ...]
    rom_sha1: str
    frames: int
    comparison_profile: str
    original: ScenarioSide
    native: ScenarioSide
    fields: tuple[ComparisonField, ...]
    landmarks: tuple[Landmark, ...]
    parameters: tuple[Parameter, ...]
    parameter_values: tuple[tuple[str, Any], ...] = ()

    @property
    def directory(self) -> Path:
        return self.path.parent

    @property
    def parameter_map(self) -> dict[str, Any]:
        return dict(self.parameter_values)


def _strings(raw: dict, name: str) -> tuple[str, ...]:
    value = raw.get(name, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f'{name} must be an array of strings')
    return tuple(value)


def _path(directory: Path, value: Any, name: str) -> Path | None:
    if value in (None, ''):
        return None
    if not isinstance(value, str):
        raise ValueError(f'{name} must be a path string')
    return (directory / value).resolve()


def _side(directory: Path, raw: Any, name: str) -> ScenarioSide:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError(f'{name} must be a table')
    input_path = _path(directory, raw.get('input'), f'{name}.input')
    input_mode = raw.get('input_mode', 'strict')
    if input_mode not in INPUT_MODES:
        raise ValueError(f'{name}.input_mode must be strict or event')
    return ScenarioSide(
        input=ScenarioFile(input_path, input_mode) if input_path else None,
        patches=_path(directory, raw.get('patches'), f'{name}.patches'),
        setup=_path(directory, raw.get('setup'), f'{name}.setup'),
        save_state=_path(directory, raw.get('save_state'), f'{name}.save_state'),
        adapter=str(raw.get('adapter', 'tetris')),
    )


def _comparison_fields(raw: Any) -> tuple[ComparisonField, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError('comparison.fields must be an array of tables')
    result = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f'comparison.fields[{index}] must be a table')
        policy = str(item.get('policy', 'exact'))
        if policy not in COMPARISON_POLICIES:
            raise ValueError(f'comparison.fields[{index}] has invalid policy {policy!r}')
        path = str(item.get('path', '')).strip()
        if not path:
            raise ValueError(f'comparison.fields[{index}] requires path')
        result.append(ComparisonField(
            path=path,
            policy=policy,
            tolerance=float(item.get('tolerance', 0.0)),
            transform=str(item.get('transform', 'identity')),
            note=str(item.get('note', '')),
        ))
    return tuple(result)


def _landmarks(raw: Any) -> tuple[Landmark, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError('landmarks must be an array of tables')
    result = []
    ids = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f'landmarks[{index}] must be a table')
        identifier = str(item.get('id', ''))
        if not IDENTIFIER_RE.fullmatch(identifier) or identifier in ids:
            raise ValueError(f'landmarks[{index}] has invalid or duplicate id')
        ids.add(identifier)
        side = str(item.get('side', 'both'))
        if side not in {'original', 'native', 'both'}:
            raise ValueError(f'landmarks[{index}] has invalid side {side!r}')
        timeout = int(item.get('timeout', 600))
        if timeout <= 0:
            raise ValueError(f'landmarks[{index}] timeout must be positive')
        condition = str(item.get('condition', '')).strip()
        if not condition:
            raise ValueError(f'landmarks[{index}] requires condition')
        result.append(Landmark(
            id=identifier,
            condition=condition,
            side=side,
            timeout=timeout,
            presentation=bool(item.get('presentation', False)),
        ))
    return tuple(result)


def _parameters(raw: Any) -> tuple[Parameter, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError('parameters must be an array of tables')
    result = []
    names = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f'parameters[{index}] must be a table')
        name = str(item.get('name', ''))
        values = item.get('values', [])
        if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', name) or name in names:
            raise ValueError(f'parameters[{index}] has invalid or duplicate name')
        if not isinstance(values, list) or not values:
            raise ValueError(f'parameters[{index}] requires nonempty values')
        names.add(name)
        result.append(Parameter(name, tuple(values)))
    return tuple(result)


def load_scenario(path: Path, *, allow_temporary: bool = False) -> Scenario:
    path = path.resolve()
    try:
        raw = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f'{path}: {error}') from error
    if raw.get('schema_version') != 1:
        raise ValueError(f'{path}: unsupported scenario schema version')
    identifier = str(raw.get('id', ''))
    validation_identifier = TEMPLATE_RE.sub('parameter', identifier)
    if not IDENTIFIER_RE.fullmatch(validation_identifier):
        raise ValueError(f'{path}: invalid scenario id {identifier!r}')
    kind = str(raw.get('kind', 'curated'))
    if kind not in SCENARIO_KINDS:
        raise ValueError(f'{path}: invalid scenario kind {kind!r}')
    if kind == 'temporary' and not allow_temporary:
        raise ValueError(f'{path}: temporary scenario requires explicit opt-in')
    directory = path.parent
    run = raw.get('run', {})
    if not isinstance(run, dict):
        raise ValueError(f'{path}: run must be a table')
    frames = int(run.get('frames', 0))
    if frames <= 0:
        raise ValueError(f'{path}: run.frames must be positive')
    comparison = raw.get('comparison', {})
    if not isinstance(comparison, dict):
        raise ValueError(f'{path}: comparison must be a table')
    rom = raw.get('rom', {})
    if not isinstance(rom, dict):
        raise ValueError(f'{path}: rom must be a table')
    sha1 = str(rom.get('sha1', '')).lower()
    if not re.fullmatch(r'[0-9a-f]{40}', sha1):
        raise ValueError(f'{path}: rom.sha1 must be a lowercase SHA-1')
    scenario = Scenario(
        path=path,
        schema_version=1,
        id=identifier,
        title=str(raw.get('title', identifier)),
        description=str(raw.get('description', '')).strip(),
        kind=kind,
        tags=_strings(raw, 'tags'),
        subsystems=_strings(raw, 'subsystems'),
        rom_sha1=sha1,
        frames=frames,
        comparison_profile=str(comparison.get('profile', 'fields')),
        original=_side(directory, raw.get('original'), 'original'),
        native=_side(directory, raw.get('native'), 'native'),
        fields=_comparison_fields(comparison.get('fields')),
        landmarks=_landmarks(raw.get('landmarks')),
        parameters=_parameters(raw.get('parameters')),
    )
    validate_scenario_files(scenario)
    if scenario.kind == 'parameterized' and not scenario.parameters:
        raise ValueError(f'{path}: parameterized scenario requires parameters')
    if scenario.kind != 'parameterized' and scenario.parameters:
        raise ValueError(f'{path}: only parameterized scenarios may define parameters')
    return scenario


def validate_scenario_files(scenario: Scenario) -> None:
    for side_name, side in (('original', scenario.original), ('native', scenario.native)):
        paths = {
            'input': side.input.path if side.input else None,
            'patches': side.patches,
            'setup': side.setup,
            'save_state': side.save_state,
        }
        for name, path in paths.items():
            if path is not None and not path.is_file():
                raise ValueError(f'{scenario.path}: {side_name}.{name} does not exist: {path}')


def discover_scenarios(root: Path, *, allow_temporary: bool = False) -> list[Scenario]:
    scenarios = []
    ids = set()
    for path in sorted(root.resolve().glob('**/scenario.toml')):
        if '.temporary' in path.parts and not allow_temporary:
            continue
        scenario = load_scenario(path, allow_temporary=allow_temporary)
        for instance in expand_scenario(scenario):
            if instance.id in ids:
                raise ValueError(f'duplicate expanded scenario id: {instance.id}')
            ids.add(instance.id)
            scenarios.append(instance)
    return scenarios


def _substitute(value: str, parameters: dict[str, Any]) -> str:
    def replace_match(match: re.Match) -> str:
        name = match.group(1)
        if name not in parameters:
            raise ValueError(f'unknown scenario parameter {name!r}')
        return str(parameters[name])
    return TEMPLATE_RE.sub(replace_match, value)


def _expand_product(parameters: tuple[Parameter, ...], index: int = 0,
                    current: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    current = {} if current is None else current
    if index == len(parameters):
        return [dict(current)]
    result = []
    parameter = parameters[index]
    for value in parameter.values:
        current[parameter.name] = value
        result.extend(_expand_product(parameters, index + 1, current))
    current.pop(parameter.name, None)
    return result


def expand_scenario(scenario: Scenario) -> list[Scenario]:
    if not scenario.parameters:
        return [scenario]
    instances = []
    for values in _expand_product(scenario.parameters):
        instances.append(replace(
            scenario,
            id=_substitute(scenario.id, values),
            title=_substitute(scenario.title, values),
            description=_substitute(scenario.description, values),
            parameters=(),
            parameter_values=tuple(values.items()),
        ))
    return instances


def find_scenario(scenarios: list[Scenario], identifier: str) -> Scenario:
    matches = [scenario for scenario in scenarios if scenario.id == identifier]
    if len(matches) != 1:
        raise ValueError(f'expected one scenario named {identifier!r}, found {len(matches)}')
    return matches[0]
