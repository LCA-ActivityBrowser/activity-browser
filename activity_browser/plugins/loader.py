# -*- coding: utf-8 -*-
"""Discover and activate Activity Browser plugins.

Flow per entry point: read package metadata → version gate → skip if disabled →
``ep.load()`` + ``activate(ctx)``. Fail-soft: one bad plugin does not stop others.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, entry_points, metadata
from typing import List, Optional

from loguru import logger

from activity_browser.plugins.context import global_plugins_settings
from activity_browser.plugins.version import PLUGINS_API_VERSION

ENTRY_POINT_GROUP = "activity_browser.plugins"


@dataclass
class PluginRecord:
    plugin_id: str
    display_name: str
    enabled: bool
    status: str  # disabled | enabled | failed | incompatible
    error: Optional[str] = None
    dist_name: Optional[str] = None
    dist_version: Optional[str] = None
    summary: Optional[str] = None


# Last load results (for Settings → Plugins)
plugin_records: List[PluginRecord] = []

# Enable-list applied for this process (restart banner compares against this)
applied_enabled_ids: set = set()


def _read_plugin_metadata(plugin_id: str, dist) -> tuple:
    """Return ``(api_version, display_name, dist_name, dist_version, summary)``."""
    api_version = None
    display_name = None
    try:
        mod = importlib.import_module(plugin_id)
    except ImportError:
        mod = None
    if mod is not None:
        version = getattr(mod, "PLUGINS_API_VERSION", None)
        if version is not None:
            api_version = str(version)
        name = getattr(mod, "PLUGIN_DISPLAY_NAME", None)
        if name:
            display_name = str(name)

    dist_name = dist_version = summary = None
    if dist is not None:
        try:
            meta = metadata(dist.name)
            dist_name, dist_version, summary = dist.name, dist.version, meta.get("Summary")
            if display_name is None and meta.get("Name"):
                display_name = meta.get("Name")
        except (PackageNotFoundError, Exception):
            dist_name = getattr(dist, "name", None)
            dist_version = getattr(dist, "version", None)

    return api_version, display_name or plugin_id, dist_name, dist_version, summary


def discover_entry_points():
    """Installed entry points in ``activity_browser.plugins`` (monkeypatched in tests)."""
    return list(entry_points(group=ENTRY_POINT_GROUP))


def load_and_activate_plugins(*, application, signals, settings) -> List[PluginRecord]:
    """Discover, filter, and activate enabled compatible plugins. Fail-soft per plugin."""
    global plugin_records, applied_enabled_ids
    from activity_browser.app import contributions as contrib
    from activity_browser.plugins.context import PluginContext

    records: List[PluginRecord] = []
    enabled_ids = set(global_plugins_settings(settings).get("enabled_plugins") or [])
    applied_enabled_ids = set(enabled_ids)

    for ep in discover_entry_points():
        plugin_id = ep.name
        enabled = plugin_id in enabled_ids
        api_version, display_name, dist_name, dist_version, summary = _read_plugin_metadata(
            plugin_id, getattr(ep, "dist", None)
        )

        record = PluginRecord(
            plugin_id=plugin_id,
            display_name=display_name,
            enabled=enabled,
            status="disabled",
            dist_name=dist_name,
            dist_version=dist_version,
            summary=summary,
        )

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
            records.append(record)
            continue

        try:
            activate = ep.load()
        except Exception as exc:
            logger.exception("Failed to load plugin entry point {}", plugin_id)
            record.status = "failed"
            record.error = str(exc)
            records.append(record)
            continue

        if not callable(activate):
            record.status = "failed"
            record.error = "Entry point did not resolve to a callable"
            records.append(record)
            continue

        try:
            ctx = PluginContext(
                plugin_id,
                application=application,
                signals=signals,
                settings=settings,
            )
            contrib.plugin_display_names[plugin_id] = record.display_name
            activate(ctx)
            record.status = "enabled"
            logger.info("Enabled plugin {}", plugin_id)
        except Exception as exc:
            logger.exception("Plugin activate failed for {}", plugin_id)
            record.status = "failed"
            record.error = str(exc)

        records.append(record)

    plugin_records = records
    return records
