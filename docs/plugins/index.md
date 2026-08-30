---
title: Plugins
nav_order: 5
---
# Plugins
{: .fs-9 }

Extend Activity Browser with third-party packages that contribute Pages, Panes, Actions, and settings.
{: .fs-6 .fw-300 }
    10|
Plugins are **global** (on or off for the whole app). Install a package that registers the `activity_browser.plugins` entry point, enable it under **Settings → Plugins**, then **Save** and **restart** Activity Browser.

Each plugin declares a **plugins API generation** (`PLUGINS_API_VERSION = "1"`, …) that must match the host; see [API version](api-reference.md#plugins-api-version) for when to bump and what stays on `"1"`.

Use the top-level **Plugins** menu for plugin actions, and **Manage plugins…** to open Settings.

## How discovery works

Python packaging describes three common ways to find plugins ([Creating and discovering plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/)):

1. **Naming convention** — import every installed module matching a prefix (e.g. `flask_*`)
2. **Namespace packages** — drop modules under a shared namespace (e.g. `myapp.plugins.*`)
3. **Package metadata (entry points)** — declare plugins in `pyproject.toml`; the host lists them with `importlib.metadata.entry_points`

Activity Browser uses **option 3**. A plugin distribution declares:

```toml
[project.entry-points."activity_browser.plugins"]
ab_example = "ab_example.activate:activate"
```

The host discovers all entry points in the `activity_browser.plugins` group. That matches the guide’s entry-point model: discovery is packaging metadata; loading the callable is a separate step (`EntryPoint.load()`).

### What Activity Browser adds on top

| Extension | Why |
|-----------|-----|
| **Enable list** | Discovered ≠ active. Users opt in under Settings; restart applies |
| **API version gate** | Package-level `PLUGINS_API_VERSION` must match the host before `activate` runs |
| **Entry-point name = package name** | e.g. `ab_example` → import package `ab_example` for display name / API version (usually constants in `__init__.py`) |
| **`activate(ctx)` + contributions** | Register Pages, Panes, Actions, menu items, settings chapters via `PluginContext` |
| **Fail-soft loading** | One bad plugin does not abort startup; status shows in Settings |

Keep the plugin package `__init__.py` **light** (metadata only). Point the entry point at `your_package.activate:activate` so UI and heavy imports load only when the plugin is enabled and activated—not merely because Settings listed it. Prefer constructor injection + a thin subclass in `activate` when pages/chapters need `ctx.settings` or `ctx.signals` (see Plugin Example).

- [Getting started](getting-started.md) — walk through Plugin Example  
- [API reference](api-reference.md) — `activity_browser.plugins`, `PluginContext`, [plugin settings](api-reference.md#plugin-settings), [integration boundaries](api-reference.md#integration-boundaries)
