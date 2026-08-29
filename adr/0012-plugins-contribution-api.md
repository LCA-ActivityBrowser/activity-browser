# Contribution-based plugins via entry points and PluginContext

Activity Browser extends itself through **Plugins** discovered as Python packaging entry points (`activity_browser.plugins`), enabled globally in Settings (restart to apply), and activated with `activate(ctx)` **before** MainWindow composition so Pages, Panes, Actions, menus, and settings chapters join first paint. Authors use the `activity_browser.plugins` facade and `PluginContext` registrations rather than AB2-style tab injection or post-UI `__import__` stubs.

Author how-to: [docs/plugins/](../plugins/index.md).

## Plugins API version

The public author surface is versioned by generation strings (`"1"`, `"2"`, …), not semver. The loader compares the host constant (`activity_browser.plugins.PLUGINS_API_VERSION`) to each plugin’s declared `PLUGINS_API_VERSION` with exact string equality before calling `activate`. Plugins pin the generation they target (e.g. `"1"`); they must not assign the host value at import time. Bump the host generation only for **breaking** plugin-facing changes; backward-compatible extensions stay on the same generation. Details: [API version](../plugins/api-reference.md#plugins-api-version).
