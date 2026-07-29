"""Scenario inclusion set S — pure algebra (no Qt)."""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Iterable, Sequence

from .utils import SCENARIO_NAME_JOIN

MODE_PRODUCT = "product"
MODE_ADDITION = "addition"

Axes = Sequence[Sequence[str]]


def join_parts(parts: Iterable[str]) -> str:
    return SCENARIO_NAME_JOIN.join(parts)


def split_combination(name: str, n_files: int) -> tuple[str, ...]:
    parts = name.split(SCENARIO_NAME_JOIN)
    if len(parts) != n_files:
        raise ValueError(
            f"Combination {name!r} has {len(parts)} parts; expected {n_files}"
        )
    return tuple(parts)


def product_universe(axes: Axes) -> list[str]:
    if not axes:
        return []
    return [join_parts(parts) for parts in itertools.product(*axes)]


def extend_universe(axes: Axes) -> list[str]:
    if not axes:
        return []
    shared = list(axes[0])
    for names in axes[1:]:
        name_set = set(names)
        shared = [n for n in shared if n in name_set]
    return shared


def full_universe(axes: Axes, mode: str) -> list[str]:
    if mode == MODE_PRODUCT:
        return product_universe(axes)
    if mode == MODE_ADDITION:
        return extend_universe(axes)
    raise ValueError(f"Unknown combine mode: {mode!r}")


def all_included(axes: Axes, mode: str) -> list[str]:
    return list(full_universe(axes, mode))


def order_included(
    included: Sequence[str], axes: Axes, mode: str
) -> list[str]:
    """Return members of S in scenario-file / product universe order."""
    included_set = set(included)
    return [name for name in full_universe(axes, mode) if name in included_set]


def derive_file_flags(
    included: Sequence[str], axes: Axes, mode: str
) -> list[list[bool]]:
    included_set = set(included)
    if mode == MODE_ADDITION:
        return [[name in included_set for name in names] for names in axes]

    n = len(axes)
    flags: list[list[bool]] = []
    for i, names in enumerate(axes):
        used = set()
        for combo in included_set:
            parts = split_combination(combo, n)
            used.add(parts[i])
        flags.append([name in used for name in names])
    return flags


def uncheck_name(
    included: Sequence[str], axes: Axes, file_index: int, name: str, mode: str
) -> list[str]:
    if mode == MODE_ADDITION:
        result = [n for n in included if n != name]
    else:
        n = len(axes)
        result = [
            combo
            for combo in included
            if split_combination(combo, n)[file_index] != name
        ]
    return order_included(result, axes, mode)


def check_name(
    included: Sequence[str], axes: Axes, file_index: int, name: str, mode: str
) -> list[str]:
    universe = set(full_universe(axes, mode))
    if mode == MODE_ADDITION:
        if name not in universe:
            return order_included(included, axes, mode)
        if name in included:
            return order_included(included, axes, mode)
        return order_included(list(included) + [name], axes, mode)

    n = len(axes)
    if name not in axes[file_index]:
        return order_included(included, axes, mode)

    flags = derive_file_flags(included, axes, mode)
    other_axes = []
    for i, names in enumerate(axes):
        if i == file_index:
            other_axes.append([name])
        else:
            on_names = [nm for nm, on in zip(names, flags[i]) if on]
            if not on_names:
                return order_included(included, axes, mode)
            other_axes.append(on_names)

    additions = [join_parts(parts) for parts in itertools.product(*other_axes)]
    seen = set(included)
    result = list(included)
    for combo in additions:
        if combo in universe and combo not in seen:
            result.append(combo)
            seen.add(combo)
    return order_included(result, axes, mode)


def toggle_combination(
    included: Sequence[str],
    combination: str,
    axes: Axes | None = None,
    mode: str | None = None,
) -> list[str]:
    if combination in included:
        result = [n for n in included if n != combination]
    else:
        result = list(included) + [combination]
    if axes is not None and mode is not None:
        return order_included(result, axes, mode)
    return result


@dataclass(frozen=True)
class ReconcileResult:
    included: list[str]
    mismatched: bool


def reconcile_included(
    saved_included: Sequence[str],
    saved_axes: Axes,
    current_axes: Axes,
    mode: str,
) -> ReconcileResult:
    """Restore S against current axes.

    If saved axes differ from current axes, treat as mismatch and return the
    full current universe. Otherwise keep saved members that still exist.
    """
    saved = [list(a) for a in saved_axes]
    current = [list(a) for a in current_axes]
    if saved != current:
        return ReconcileResult(all_included(current_axes, mode), mismatched=True)

    universe = full_universe(current_axes, mode)
    universe_set = set(universe)
    kept = [n for n in universe if n in set(saved_included) & universe_set]
    return ReconcileResult(kept, mismatched=False)
