# -*- coding: utf-8 -*-
"""Plugin Example — pedagogical Activity Browser plugin."""

from .activate import activate

# API contract this plugin was written against (must match the host at load time).
PLUGINS_API_VERSION = "1"
PLUGIN_DISPLAY_NAME = "Plugin Example"

__all__ = ["PLUGINS_API_VERSION", "PLUGIN_DISPLAY_NAME", "activate"]
