#!/usr/bin/env python3

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

from scenario_model import ComparisonField


PATH_PART_RE = re.compile(r'([^.[\]]+)|\[(\d+)\]')


@dataclass(frozen=True)
class Difference:
    path: str
    policy: str
    original: Any
    native: Any
    message: str
    failure: bool


@dataclass(frozen=True)
class ComparisonResult:
    differences: tuple[Difference, ...]

    @property
    def matches(self) -> bool:
        return not any(item.failure for item in self.differences)


def value_at(document: Any, path: str) -> Any:
    value = document
    consumed = ''
    for match in PATH_PART_RE.finditer(path):
        if match.start() != len(consumed) and path[len(consumed):match.start()] != '.':
            raise ValueError(f'invalid observation path {path!r}')
        consumed = path[:match.end()]
        if match.group(1) is not None:
            if not isinstance(value, dict) or match.group(1) not in value:
                raise KeyError(path)
            value = value[match.group(1)]
        else:
            index = int(match.group(2))
            if not isinstance(value, (list, tuple)) or index >= len(value):
                raise KeyError(path)
            value = value[index]
    if consumed != path:
        raise ValueError(f'invalid observation path {path!r}')
    return value


def _identity(value: Any) -> Any:
    return value


def _music_id_to_index(value: Any) -> Any:
    return int(value) - 1 if int(value) else -1


def _truthy(value: Any) -> bool:
    return bool(value)


def _lower(value: Any) -> str:
    return str(value).lower()


TRANSFORMS: dict[str, Callable[[Any], Any]] = {
    'identity': _identity,
    'music_id_to_index': _music_id_to_index,
    'truthy': _truthy,
    'lower': _lower,
}


def compare_field(field: ComparisonField, original_document: dict,
                  native_document: dict) -> Difference | None:
    if field.policy == 'ignore':
        return None
    try:
        original = value_at(original_document, field.path)
        native = value_at(native_document, field.path)
    except (KeyError, ValueError) as error:
        return Difference(field.path, field.policy, None, None,
                          f'missing or invalid field: {error}', True)
    if field.policy == 'intentional_difference':
        return Difference(field.path, field.policy, original, native,
                          field.note or 'reviewed intentional difference', False)
    if field.policy == 'transform':
        transform = TRANSFORMS.get(field.transform)
        if transform is None:
            return Difference(field.path, field.policy, original, native,
                              f'unknown transform {field.transform!r}', True)
        try:
            original = transform(original)
            native = transform(native)
        except (TypeError, ValueError, OverflowError) as error:
            return Difference(
                field.path, field.policy, original, native,
                f'transform {field.transform!r} failed: {error}', True,
            )
    if field.policy == 'tolerance':
        try:
            matches = abs(float(original) - float(native)) <= field.tolerance
        except (TypeError, ValueError):
            matches = False
    elif field.policy == 'ordered':
        matches = (
            isinstance(original, (list, tuple)) and
            isinstance(native, (list, tuple)) and
            list(original) == list(native)
        )
    else:
        matches = original == native
    if matches:
        return None
    return Difference(
        field.path, field.policy, original, native,
        f'original={original!r}, native={native!r}', True,
    )


def compare_observations(fields: tuple[ComparisonField, ...], original: dict,
                         native: dict) -> ComparisonResult:
    differences = []
    for field in fields:
        difference = compare_field(field, original, native)
        if difference is not None:
            differences.append(difference)
    return ComparisonResult(tuple(differences))
