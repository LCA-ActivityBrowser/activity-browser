# -*- coding: utf-8 -*-
"""Plugin Example — pedagogical Activity Browser plugin.

Keep this module light: the host imports the package for metadata even when the
plugin is disabled. Thus this module should at best not import any other modules. The entry point (where importing can start) is in ``activate.py``. This is loaded when a plugin is enabled.
"""

# API contract this plugin was written against (must match the host at load time).
PLUGINS_API_VERSION = "1"
PLUGIN_DISPLAY_NAME = "Plugin Example"

__all__ = ["PLUGINS_API_VERSION", "PLUGIN_DISPLAY_NAME"]
