#!/usr/bin/env python3

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scenario_compare import value_at


KEYS = {'A', 'B', 'SELECT', 'START', 'RIGHT', 'LEFT', 'UP', 'DOWN'}
CONDITION_RE = re.compile(r'^\s*([a-zA-Z0-9_.\[\]-]+)\s*(==|!=|<=|>=|<|>)\s*(.*?)\s*$')


@dataclass(frozen=True)
class StrictInput:
    tick: int
    keys: tuple[str, ...]


@dataclass(frozen=True)
class EventInput:
    action: str
    keys: tuple[str, ...]
    condition: str
    timeout: int


def parse_keys(text: str) -> tuple[str, ...]:
    text = text.strip().upper()
    if not text or text == 'NONE':
        return ()
    keys = tuple(filter(None, re.split(r'[+|\s]+', text)))
    unknown = set(keys) - KEYS
    if unknown:
        raise ValueError(f'unknown input keys: {sorted(unknown)}')
    return keys


def load_strict_inputs(path: Path) -> list[StrictInput]:
    result = []
    previous = -1
    with path.open(newline='') as source:
        for line_number, row in enumerate(csv.reader(source), 1):
            if not row or row[0].lstrip().startswith('#'):
                continue
            if len(row) != 2:
                raise ValueError(f'{path}:{line_number}: expected tick,keys')
            try:
                tick = int(row[0], 0)
            except ValueError as error:
                raise ValueError(f'{path}:{line_number}: invalid tick') from error
            if tick <= previous:
                raise ValueError(f'{path}:{line_number}: ticks must increase')
            result.append(StrictInput(tick, parse_keys(row[1])))
            previous = tick
    if not result:
        raise ValueError(f'{path}: strict input is empty')
    return result


def load_event_inputs(path: Path) -> list[EventInput]:
    result = []
    with path.open(newline='') as source:
        rows = csv.DictReader(line for line in source if not line.lstrip().startswith('#'))
        required = {'action', 'keys', 'condition', 'timeout'}
        if rows.fieldnames is None or not required.issubset(rows.fieldnames):
            raise ValueError(f'{path}: event input requires {sorted(required)} columns')
        for line_number, row in enumerate(rows, 2):
            action = row['action'].strip().lower()
            if action not in {'wait', 'tap', 'hold', 'release'}:
                raise ValueError(f'{path}:{line_number}: invalid action {action!r}')
            try:
                timeout = int(row['timeout'], 0)
            except ValueError as error:
                raise ValueError(f'{path}:{line_number}: invalid timeout') from error
            if timeout <= 0:
                raise ValueError(f'{path}:{line_number}: timeout must be positive')
            condition = row['condition'].strip()
            if condition:
                parse_condition(condition)
            result.append(EventInput(action, parse_keys(row['keys']), condition, timeout))
    if not result:
        raise ValueError(f'{path}: event input is empty')
    return result


def _literal(text: str) -> Any:
    text = text.strip()
    if text.lower() in {'true', 'false'}:
        return text.lower() == 'true'
    if text.lower() in {'null', 'none'}:
        return None
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        return text[1:-1]
    try:
        return int(text, 0)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text


def parse_condition(condition: str) -> tuple[str, str, Any]:
    match = CONDITION_RE.fullmatch(condition)
    if not match:
        raise ValueError(f'invalid condition {condition!r}')
    return match.group(1), match.group(2), _literal(match.group(3))


def condition_matches(condition: str, observation: dict) -> bool:
    path, operator, expected = parse_condition(condition)
    try:
        actual = value_at(observation, path)
    except (KeyError, ValueError):
        return False
    operations = {
        '==': lambda: actual == expected,
        '!=': lambda: actual != expected,
        '<': lambda: actual < expected,
        '<=': lambda: actual <= expected,
        '>': lambda: actual > expected,
        '>=': lambda: actual >= expected,
    }
    try:
        return operations[operator]()
    except TypeError:
        return False
