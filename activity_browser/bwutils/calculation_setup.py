"""Calculation setup helpers (Brightway ``inv`` / ``ia`` lists)."""

from __future__ import annotations

import bw2data as bd

INV_ACTIVE = "inv_active"
IA_ACTIVE = "ia_active"
_ACTIVE = {"inv": INV_ACTIVE, "ia": IA_ACTIVE}


def active_flags(cs: dict, list_key: str) -> list[bool]:
    n = len(cs.get(list_key, []))
    flags = cs.get(_ACTIVE[list_key]) or [True] * n
    flags = list(flags) + [True] * max(0, n - len(flags))
    return [bool(v) for v in flags[:n]]


def ensure_active_lists(cs: dict) -> None:
    cs[INV_ACTIVE] = active_flags(cs, "inv")
    cs[IA_ACTIVE] = active_flags(cs, "ia")


def move_rows(items: list, flags: list[bool], rows: list[int], dest: int) -> None:
    rows = sorted(set(rows))
    if not rows:
        return
    chunk = [(items[i], flags[i]) for i in rows]
    for i in reversed(rows):
        del items[i]
        del flags[i]
    dest = max(0, min(dest, len(items)))
    dest -= sum(1 for i in rows if i < dest)
    for offset, (item, flag) in enumerate(chunk):
        items.insert(dest + offset, item)
        flags.insert(dest + offset, flag)


def _save(cs_name: str, cs: dict) -> None:
    bd.calculation_setups[cs_name] = cs
    bd.calculation_setups.serialize()


def set_active(cs_name: str, list_key: str, row: int, active: bool) -> None:
    cs = bd.calculation_setups[cs_name]
    ensure_active_lists(cs)
    cs[_ACTIVE[list_key]][row] = bool(active)
    _save(cs_name, cs)


def reorder(cs_name: str, list_key: str, rows: list[int], dest: int) -> None:
    cs = bd.calculation_setups[cs_name]
    ensure_active_lists(cs)
    move_rows(cs[list_key], cs[_ACTIVE[list_key]], rows, dest)
    _save(cs_name, cs)


def active_calculation_setup(cs_name: str) -> dict:
    cs = dict(bd.calculation_setups[cs_name])
    ensure_active_lists(cs)
    cs["inv"] = [fu for fu, ok in zip(cs["inv"], cs[INV_ACTIVE]) if ok]
    cs["ia"] = [m for m, ok in zip(cs["ia"], cs[IA_ACTIVE]) if ok]
    return cs
