# -*- coding: utf-8 -*-
"""Thin adapter over PluginContext host capabilities."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterable, Iterator


class ShreccPluginHost:
    def __init__(self, ctx) -> None:
        self._ctx = ctx

    @contextmanager
    def protect_databases(
        self,
        names: Iterable[str],
        *,
        reason: str = "SHRECC create",
    ) -> Iterator[None]:
        with self._ctx.protect_databases(names, reason=reason):
            yield
