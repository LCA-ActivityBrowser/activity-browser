# -*- coding: utf-8 -*-
"""Thin adapter over PluginContext host capabilities."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Callable, Iterable, Iterator


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

    def after_database_write(self, db_name: str, *, notify: bool = True) -> None:
        self._ctx.after_database_write(db_name, notify=notify)

    def run_blocking_operation(
        self,
        title: str,
        func: Callable[[], Any],
        *,
        cancellable: bool = False,
    ) -> Any:
        return self._ctx.run_blocking_operation(
            title,
            func,
            cancellable=cancellable,
        )
