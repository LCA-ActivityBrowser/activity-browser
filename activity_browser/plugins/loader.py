# -*- coding: utf-8 -*-
"""Discover and activate Activity Browser plugins."""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, entry_points, metadata
from typing import Any, Callable, List, Optional

from loguru import logger

from activity_browser.plugins.version import PLUGINS_API_VERSION

ENTRY_POINT_GROUP = "activity_browser.plugins"


@dataclass
class PluginRecord:
    plugin_id: str
    display_name: str
    enabled: bool
    status: str  # disabled | loaded | failed | incompatible
    error: Optional[str] = None
    dist_name: Optional[str] = None
    dist_version: Optional[str] = None
    summary: Optional[str] = None


# Last load results (for Settings UI)
plugin_records: List[PluginRecord] = []

# Entry-point ids that were in enabled_plugins when this process loaded plugins
applied_enabled_ids: set = set()


def _enabled_plugin_ids(settings) -> set:
    enabled = settings["plugins"].get("enabled_plugins") or []
    return set(enabled)


def _entry_point_package_names(activate: Callable, plugin_id: str) -> List[str]:
    names: List[str] = []
    module_name = getattr(activate, "__module__", None)
    if module_name and "." in module_name:
        names.append(module_name.rsplit(".", 1)[0])
    if plugin_id not in names:
        names.append(plugin_id)
    return names


def _read_api_version(activate: Callable, module, plugin_id: str) -> Optional[str]:
    candidates = []
    if module is not None:
        candidates.append(module)

    import importlib

    for pkg_name in _entry_point_package_names(activate, plugin_id):
        try:
            pkg = importlib.import_module(pkg_name)
        except ImportError:
            continue
        if pkg not in candidates:
            candidates.append(pkg)

    for candidate in candidates:
        version = getattr(candidate, "PLUGINS_API_VERSION", None)
        if version is not None:
            return str(version)

    version = getattr(activate, "plugins_api_version", None)
    if version is None:
        return None
    return str(version)


def _display_name(activate: Callable, module, plugin_id: str, dist) -> str:
    name = getattr(module, "PLUGIN_DISPLAY_NAME", None)
    if name:
        return str(name)
    if dist is not None:
        try:
            meta = metadata(dist.name)
            summary_name = meta.get("Name")
            if summary_name:
                return summary_name
        except Exception:
            pass
    return plugin_id


def _dist_info(ep) -> tuple:
    dist = getattr(ep, "dist", None)
    if dist is None:
        return None, None, None
    try:
        meta = metadata(dist.name)
        return dist.name, dist.version, meta.get("Summary")
    except (PackageNotFoundError, Exception):
        return getattr(dist, "name", None), getattr(dist, "version", None), None


def discover_entry_points():
    return list(entry_points(group=ENTRY_POINT_GROUP))


def load_and_activate_plugins(*, application, signals, settings, pages=None, panes=None) -> List[PluginRecord]:
    """Discover, filter, and activate enabled compatible plugins. Fail-soft per plugin."""
    global plugin_records, applied_enabled_ids
    from activity_browser.app import contributions as contrib

    records: List[PluginRecord] = []
    enabled_ids = _enabled_plugin_ids(settings)
    applied_enabled_ids = set(enabled_ids)

    for ep in discover_entry_points():
        plugin_id = ep.name
        dist_name, dist_version, summary = _dist_info(ep)
        enabled = plugin_id in enabled_ids

        record = PluginRecord(
            plugin_id=plugin_id,
            display_name=plugin_id,
            enabled=enabled,
            status="disabled",
            dist_name=dist_name,
            dist_version=dist_version,
            summary=summary,
        )

        try:
            activate = ep.load()
        except Exception as exc:
            logger.exception("Failed to load plugin entry point {}", plugin_id)
            record.status = "failed"
            record.error = str(exc)
            records.append(record)
            continue

        module = getattr(activate, "__module__", None)
        mod = None
        if module:
            import importlib

            mod = importlib.import_module(module)

        record.display_name = _display_name(activate, mod, plugin_id, getattr(ep, "dist", None))
        api_version = _read_api_version(activate, mod, plugin_id)

        if api_version != PLUGINS_API_VERSION:
            record.status = "incompatible"
            record.error = (
                f"Plugin API {api_version!r} incompatible with host {PLUGINS_API_VERSION!r}"
                if api_version is not None
                else f"Missing PLUGINS_API_VERSION (host requires {PLUGINS_API_VERSION!r})"
            )
            logger.warning("Skipping incompatible plugin {}: {}", plugin_id, record.error)
            records.append(record)
            continue

        if not enabled:
            record.status = "disabled"
            records.append(record)
            continue

        if not callable(activate):
            record.status = "failed"
            record.error = "Entry point did not resolve to a callable"
            records.append(record)
            continue

        try:
            from activity_browser.plugins.context import PluginContext

            ctx = PluginContext(
                plugin_id,
                application=application,
                signals=signals,
                settings=settings,
            )
            contrib.plugin_display_names[plugin_id] = record.display_name
            activate(ctx)
            record.status = "loaded"
            logger.info("Loaded plugin {}", plugin_id)
        except Exception as exc:
            logger.exception("Plugin activate failed for {}", plugin_id)
            record.status = "failed"
            record.error = str(exc)

        records.append(record)

    plugin_records = records
    return records
