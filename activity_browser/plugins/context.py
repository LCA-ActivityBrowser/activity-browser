# -*- coding: utf-8 -*-
"""PluginContext — registration object passed to activate(ctx)."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Callable, Iterator, Iterable, Optional, Type


def global_plugins_settings(settings: Any) -> dict:
    """Return ``settings.global_config["plugins"]``, creating it if missing.

    Use this for the enable list and per-plugin ``data`` so reads/writes hit the
    dict that Settings Save persists — not ``settings["plugins"]`` (which can
    resolve to module-level defaults).
    """
    if "plugins" not in settings.global_config:
        settings.global_config["plugins"] = {
            "enabled_plugins": [],
            "data": {},
        }
    plugins = settings.global_config["plugins"]
    plugins.setdefault("enabled_plugins", [])
    plugins.setdefault("data", {})
    return plugins


def _ensure_shown_startup(settings: Any, list_key: str, contribution_id: str) -> None:
    import copy

    from activity_browser.bwutils.settings import defaults

    if "startup" not in settings.global_config:
        settings.global_config["startup"] = copy.deepcopy(defaults["startup"])
    shown = settings.global_config["startup"].setdefault(list_key, [])
    if contribution_id not in shown:
        shown.append(contribution_id)


class _PluginSettingsView:
    """Namespaced prefs: ``global_config["plugins"]["data"][plugin_id]``."""

    def __init__(self, settings: Any, plugin_id: str):
        self._settings = settings
        self._plugin_id = plugin_id

    def _data(self) -> dict:
        return global_plugins_settings(self._settings)["data"].setdefault(
            self._plugin_id, {}
        )

    def get(self, key, default=None):
        return self._data().get(key, default)

    def __getitem__(self, key):
        return self._data()[key]

    def __setitem__(self, key, value):
        self._data()[key] = value

    def __contains__(self, key):
        return key in self._data()


class PluginContext:
    """Host-owned registration API for a single plugin ``activate(ctx)`` call."""

    def __init__(
        self,
        plugin_id: str,
        *,
        application,
        signals,
        settings,
    ):
        self.plugin_id = plugin_id
        self.application = application
        self.signals = signals
        self.settings = _PluginSettingsView(settings, plugin_id)
        self._settings = settings

    def _require_namespaced_id(self, contribution_id: str) -> None:
        prefix = f"{self.plugin_id}."
        if not contribution_id.startswith(prefix) or contribution_id == prefix:
            raise ValueError(
                f"Contribution id {contribution_id!r} must be namespaced as "
                f"'{self.plugin_id}.<local>'"
            )

    def register_page(
        self,
        contribution_id: str,
        page_class: Type,
        *,
        title: Optional[str] = None,
        show_by_default: bool = True,
    ) -> None:
        from activity_browser.app import pages

        self._require_namespaced_id(contribution_id)
        if contribution_id in pages.base_pages:
            raise ValueError(f"Page id already registered: {contribution_id!r}")
        if title is not None:
            page_class = type(
                page_class.__name__,
                (page_class,),
                {"title": title, "name": contribution_id, "basePage": True},
            )
        elif not getattr(page_class, "basePage", False):
            page_class = type(
                page_class.__name__,
                (page_class,),
                {
                    "basePage": True,
                    "name": getattr(page_class, "name", None) or contribution_id,
                },
            )
        pages.base_pages[contribution_id] = page_class
        if show_by_default:
            _ensure_shown_startup(self._settings, "shown_pages", contribution_id)

    def register_pane(
        self,
        contribution_id: str,
        pane_class: Type,
        *,
        title: Optional[str] = None,
        show_by_default: bool = True,
    ) -> None:
        from activity_browser.app import panes

        self._require_namespaced_id(contribution_id)
        if contribution_id in panes.base_panes:
            raise ValueError(f"Pane id already registered: {contribution_id!r}")
        if title is not None:
            pane_class = type(
                pane_class.__name__,
                (pane_class,),
                {"title": title, "name": contribution_id},
            )
        panes.base_panes[contribution_id] = pane_class
        if show_by_default:
            _ensure_shown_startup(self._settings, "shown_panes", contribution_id)

    def register_action(self, contribution_id: str, action_class: Type) -> None:
        from activity_browser.app import contributions as contrib

        self._require_namespaced_id(contribution_id)
        contrib.register_action(contribution_id, action_class)

    def register_menu_item(self, menu_path: str, action_id: str) -> None:
        from activity_browser.app import contributions as contrib

        self._require_namespaced_id(action_id)
        contrib.plugin_submenu_items.setdefault(self.plugin_id, []).append(
            (menu_path, action_id)
        )

    def register_settings_chapter(
        self,
        contribution_id: str,
        chapter_class: Type,
        *,
        title: Optional[str] = None,
    ) -> None:
        from activity_browser.app import contributions as contrib

        self._require_namespaced_id(contribution_id)
        contrib.register_settings_chapter(
            contribution_id,
            chapter_class,
            title=title or contribution_id,
        )

    @contextmanager
    def protect_databases(
        self,
        names: Iterable[str],
        *,
        reason: str = "",
    ) -> Iterator[None]:
        """Temporarily block user edit/delete on the named databases."""
        from .database_protection import protect_databases as _protect

        with _protect(names, plugin_id=self.plugin_id, reason=reason):
            yield

    def run_blocking_operation(
        self,
        title: str,
        func: Callable[[], Any],
        *,
        cancellable: bool = False,
    ) -> Any:
        """Run ``func`` on a worker thread with modal progress (database-write style)."""
        from activity_browser import app
        from .blocking_operation import run_blocking_operation as _run

        parent = getattr(app, "main_window", None)
        if parent is None:
            raise RuntimeError("run_blocking_operation requires Activity Browser main window")
        return _run(parent, title, func, cancellable=cancellable)

    @contextmanager
    def safe_bw_connection(self) -> Iterator[None]:
        """Close Brightway/peewee connections for this thread on exit (worker threads)."""
        from .safe_bw_connection import safe_bw_connection as _safe

        with _safe():
            yield
