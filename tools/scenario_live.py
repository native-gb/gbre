#!/usr/bin/env python3

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mgba_service import MgbaService, MgbaServiceError
from scenario_compare import ComparisonResult, compare_observations
from scenario_inputs import (EventInput, StrictInput, condition_matches,
                             load_event_inputs, load_strict_inputs)
from scenario_model import Scenario
from tetris_normalize import MENU_STATES, normalize_original


KEY_BITS = {
    'A': 1 << 0,
    'B': 1 << 1,
    'SELECT': 1 << 2,
    'START': 1 << 3,
    'RIGHT': 1 << 4,
    'LEFT': 1 << 5,
    'UP': 1 << 6,
    'DOWN': 1 << 7,
}


@dataclass(frozen=True)
class ScheduledPatch:
    frame: int
    address: int
    value: int


def key_mask(keys: tuple[str, ...] | list[str]) -> int:
    mask = 0
    for key in keys:
        mask |= KEY_BITS[key]
    return mask


def load_patches(path: Path | None) -> list[ScheduledPatch]:
    if path is None:
        return []
    patches = []
    previous = -1
    with path.open(newline='') as source:
        for line_number, row in enumerate(csv.reader(source), 1):
            if not row or row[0].lstrip().startswith('#'):
                continue
            if len(row) != 3:
                raise ValueError(f'{path}:{line_number}: expected frame,address,value')
            frame, address, value = (int(item, 0) for item in row)
            if frame < previous or not 0 <= address <= 0xFFFF or not 0 <= value <= 0xFF:
                raise ValueError(f'{path}:{line_number}: invalid or out-of-order patch')
            patches.append(ScheduledPatch(frame, address, value))
            previous = frame
    return patches


class LiveScenarioSession:
    def __init__(self, service: MgbaService):
        self.service = service
        self.scenario: Scenario | None = None
        self.strict_inputs: list[StrictInput] = []
        self.event_inputs: list[EventInput] = []
        self.patches: list[ScheduledPatch] = []
        self.input_index = 0
        self.patch_index = 0
        self.event_index = 0
        self.held_mask = 0
        self.seen_menu = False
        self.last_original: dict[str, Any] | None = None
        self.recorded_inputs: list[tuple[int, int]] = []

    def load(self, scenario: Scenario) -> dict[str, Any]:
        self.scenario = scenario
        self.strict_inputs = []
        self.event_inputs = []
        if scenario.original.input is not None:
            if scenario.original.input.mode == 'strict':
                self.strict_inputs = load_strict_inputs(scenario.original.input.path)
            else:
                self.event_inputs = load_event_inputs(scenario.original.input.path)
        self.patches = load_patches(scenario.original.patches)
        song_id = scenario.parameter_map.get('song_id')
        if song_id is not None:
            self.patches.append(ScheduledPatch(700, 0xDFE8, int(song_id)))
            self.patches.sort(key=lambda patch: patch.frame)
        return self.reset()

    def reset(self) -> dict[str, Any]:
        scenario = self._require_scenario()
        self.service.reset()
        if scenario.original.save_state:
            self.service.load_state(scenario.original.save_state, scenario.id)
        self.input_index = 0
        self.patch_index = 0
        self.event_index = 0
        self.held_mask = 0
        self.seen_menu = False
        self.last_original = None
        self.recorded_inputs.clear()
        self.service.set_keys(0)
        self._apply_scheduled(self._frame())
        return self.observe()

    def _require_scenario(self) -> Scenario:
        if self.scenario is None:
            raise MgbaServiceError('no live scenario is loaded')
        return self.scenario

    def _raw(self) -> dict[str, Any]:
        return self.service.observe()

    def _frame(self) -> int:
        return int(self._raw()['clock']['emulator_frame'])

    def _apply_scheduled(self, frame: int) -> None:
        while (self.input_index < len(self.strict_inputs) and
               self.strict_inputs[self.input_index].tick <= frame):
            event = self.strict_inputs[self.input_index]
            self.held_mask = key_mask(event.keys)
            self.service.set_keys(self.held_mask)
            self.input_index += 1
        while (self.patch_index < len(self.patches) and
               self.patches[self.patch_index].frame <= frame):
            patch = self.patches[self.patch_index]
            self.service.write(patch.address, patch.value)
            self.patch_index += 1

    def step(self, frames: int = 1) -> dict[str, Any]:
        self._require_scenario()
        if frames <= 0:
            raise ValueError('frames must be positive')
        if self.last_original is None:
            current_frame = self._frame()
        else:
            current_frame = int(self.last_original['clock']['emulator_frame'])
        for _ in range(frames):
            self._apply_scheduled(current_frame + 1)
            self.service.step()
            current_frame += 1
        return self.observe()

    def set_keys(self, mask: int) -> dict[str, Any]:
        self.held_mask = mask
        self.service.set_keys(mask)
        frame = self._frame()
        if not self.recorded_inputs or self.recorded_inputs[-1][1] != mask:
            self.recorded_inputs.append((frame, mask))
        return self.observe()

    def observe(self) -> dict[str, Any]:
        raw = self._raw()
        frame = raw['clock']['emulator_frame']
        if (self.last_original is not None and
                self.last_original['clock']['emulator_frame'] == frame):
            return self.last_original
        if raw['game']['state'] in MENU_STATES:
            self.seen_menu = True
        observation = normalize_original(raw, seen_menu=self.seen_menu)
        observation['events'] = self._events(observation)
        self.last_original = observation
        return observation

    def _events(self, current: dict[str, Any]) -> list[dict[str, Any]]:
        previous = self.last_original
        if previous is None:
            return []
        events = []

        def emit(kind: str, value: int = 0) -> None:
            events.append({'type': kind, 'value': value})

        old_game = previous['game']
        game = current['game']
        old_piece = old_game['active_piece']
        piece = game['active_piece']
        if piece['code'] != old_piece['code']:
            if piece['code'] & 0xFC == old_piece['code'] & 0xFC:
                emit('piece-rotated', piece['code'] & 3)
            else:
                emit('piece-spawned', piece['code'])
        if piece['x'] != old_piece['x'] or piece['y'] != old_piece['y']:
            emit('piece-moved', piece['x'] - old_piece['x']
                 if piece['y'] == old_piece['y'] else 0)
        if game['lines'] != old_game['lines']:
            emit('lines-cleared', game['lines'] - old_game['lines'])
        if game['score'] != old_game['score']:
            emit('score-changed', game['score'])
        if game['level'] != old_game['level']:
            emit('level-changed', game['level'])
        if game['paused'] != old_game['paused']:
            emit('paused', 1 if game['paused'] else 0)
        if game['preview_hidden'] != old_game['preview_hidden']:
            emit('preview-visibility', 1 if game['preview_hidden'] else 0)
        return events

    def advance_landmark(self, condition: str, timeout: int) -> dict[str, Any]:
        for _ in range(timeout + 1):
            observation = self.observe()
            if condition_matches(condition, observation):
                return observation
            self.step()
        raise MgbaServiceError(
            f'landmark {condition!r} was not reached within {timeout} frames'
        )

    def advance_next_event(self) -> dict[str, Any]:
        if self.event_index >= len(self.event_inputs):
            raise MgbaServiceError('event input sequence is complete')
        event = self.event_inputs[self.event_index]
        self.event_index += 1
        if event.action == 'hold':
            self.held_mask |= key_mask(event.keys)
            self.service.set_keys(self.held_mask)
        elif event.action == 'release':
            self.held_mask &= ~key_mask(event.keys)
            self.service.set_keys(self.held_mask)
        elif event.action == 'tap':
            self.service.set_keys(self.held_mask | key_mask(event.keys))
            self.service.step()
            self.service.set_keys(self.held_mask)
        if not event.condition:
            return self.observe()
        return self.advance_landmark(event.condition, event.timeout)

    def compare(self, native: dict[str, Any]) -> ComparisonResult:
        scenario = self._require_scenario()
        return compare_observations(scenario.fields, self.observe(), native)
