---
title: Plugins
nav_order: 5
---
# Plugins
{: .fs-9 }

Extend Activity Browser with third-party packages that contribute Pages, Panes, Actions, and settings.
{: .fs-6 .fw-300 }

Plugins are **global** (on or off for the whole app). Install a package that registers the `activity_browser.plugins` entry point, enable it under **Settings → Plugins**, then **Save** and **restart** Activity Browser.

Each plugin declares a **plugins API generation** (`PLUGINS_API_VERSION = "1"`, …) that must match the host; see [API version](api-reference.md#plugins-api-version) for when to bump and what stays on `"1"`.

Use the top-level **Plugins** menu for plugin actions, and **Manage plugins…** to open Settings.

- [Getting started](getting-started.md) — walk through Plugin Example  
- [API reference](api-reference.md) — `activity_browser.plugins`, `PluginContext`, [integration boundaries](api-reference.md#integration-boundaries)
