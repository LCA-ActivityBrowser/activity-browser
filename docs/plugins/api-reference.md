---
title: API reference
parent: Plugins
---
# Plugins API reference
{: .fs-9 }

Stable author surface for Activity Browser plugins.
{: .fs-6 .fw-300 }

Import only from `activity_browser.plugins` (plus Brightway / stdlib / other third-party packages). Other `activity_browser.*` modules are **unsupported**.

## Exports

| Name | Role |
|---|---|
| `PLUGINS_API_VERSION` | Host’s current plugins API generation (see [API version](#plugins-api-version)) |
| `PluginContext` | Registration object passed to `activate` |
| `ABAbstractPage` | Base for `register_page` |
| `ABAbstractPane` | Base for `register_pane` |
| `ABAction` | Base for `register_action` |
| `BaseSettingsChapter` | Base for `register_settings_chapter` |
| `reveal_page` / `reveal_pane` | Focus a registered page/pane by contribution id |

## Declaring a plugin

```toml
[project.entry-points."activity_browser.plugins"]
my_plugin = "my_plugin.activate:activate"
```

```python
# my_plugin/__init__.py — metadata only
PLUGINS_API_VERSION = "1"  # required — see [API version](#plugins-api-version)
PLUGIN_DISPLAY_NAME = "My Plugin"  # optional
```

```python
# my_plugin/activate.py
from activity_browser.plugins import PluginContext

def activate(ctx: PluginContext) -> None:
    ...
```

## Plugins API version

Activity Browser and each plugin both declare a **plugins API generation**: `"1"`, `"2"`, `"3"`, …
This is **not** semver (`1.0`, `1.1`) and **not** your plugin’s package version in `pyproject.toml`.

### What it means

- **Host** (`activity_browser.plugins.PLUGINS_API_VERSION`): the contract generation Activity Browser implements today.
- **Plugin** (module-level `PLUGINS_API_VERSION` on your entry-point package, usually `__init__.py`): the generation your plugin was **written and tested against**.

At startup the loader compares these strings with **exact equality**. Match → plugin may load (if enabled). Mismatch or missing constant → status **Incompatible**; `activate()` is not called.

### What to put in your plugin

Pin a literal string for the API you target:

```python
PLUGINS_API_VERSION = "1"
```

Do **not** copy the host value at import time:

```python
# Wrong — disables the compatibility check
from activity_browser.plugins import PLUGINS_API_VERSION as HOST
PLUGINS_API_VERSION = HOST
```

You may **read** the host constant while developing to see what AB ships, but your declared version should stay pinned until you intentionally update it.

### Where the loader looks

Entry-point **name** must match the plugin’s top-level package (e.g. entry point `ab_example` → package `ab_example`). The loader reads `PLUGINS_API_VERSION` and `PLUGIN_DISPLAY_NAME` from that package (usually `__init__.py`). `activate` may live in a submodule (e.g. `activate.py`); metadata stays on the package.

### When Activity Browser changes the API

| Change | Bump host to `"2"`? | Existing `"1"` plugins |
|--------|---------------------|-------------------------|
| Backward-compatible extension (new optional `register_*` argument, new export old plugins ignore) | **No** — stay on `"1"` | Keep working unchanged |
| Breaking change (removed/renamed registration, stricter rules, changed base-class contract) | **Yes** | Show **Incompatible** until authors update code and set `PLUGINS_API_VERSION = "2"` |

**Rule of thumb:** if a plugin written for `"1"` should still run on the new release without code changes, do **not** bump the API version — document the addition in release notes and this reference instead.

### Maintainer vs plugin author

- **AB maintainers** bump `activity_browser/plugins/version.py` only for breaking plugin-facing changes.
- **Plugin authors** bump their own `PLUGINS_API_VERSION` when they have adapted to a new generation and want to run on that AB release.

Users see incompatible plugins under **Settings → Plugins** with an error such as `Plugin API '1' incompatible with host '2'`.

## PluginContext

- `ctx.plugin_id`, `ctx.signals` (listen), `ctx.settings` (namespaced), `ctx.application`
- `register_page(id, page_class, *, title=None, show_by_default=True)` — by default adds the page id to startup `shown_pages` so it opens after enable + restart. Pass `False` to hide optional/secondary UI; users can still change visibility via Settings → Startup / View.
- `register_pane(id, pane_class, *, title=None, show_by_default=True)` — same for startup `shown_panes`.
- `register_action(id, action_class)`
- `register_menu_item(menu_path, action_id)` — path relative to **Plugins → \<plugin\>**
- `register_settings_chapter(id, chapter_class, *, title=None)`

Contribution IDs must be `plugin_id.local`. No `main_window`, raw registries, or `register_signal`.

Pages, panes, and settings chapters are constructed later by the host **without** `ctx`. If a contribution needs `ctx.settings` or `ctx.signals`, bind them in `activate` (thin subclass that closes over those values) so multiple enabled plugins stay isolated. Do not assign `ctx` onto shared class attributes.

## Plugin settings

There are two different “settings” surfaces. Do not confuse them.

### 1. Enable / disable the plugin (host)

Users turn plugins on under **Settings → Plugins**. That writes the global enable list (`enabled_plugins`). Changes apply only after **Save** and **restart**. Your plugin code does not register this — the host discovers entry points and owns that UI.

### 2. Your plugin’s own preferences (`ctx.settings`)

`ctx.settings` is a **namespaced** view of  
`settings.global_config["plugins"]["data"][<your plugin_id>]`.

Use it for small prefs (strings, flags, numbers). Keys are local to your plugin; you will not see another plugin’s data.

```python
# In activate, or in UI after binding ctx.settings into the class:
ctx.settings["greeting"] = "Hello"
greeting = ctx.settings.get("greeting", "Hello")
```

Values live in memory on ``settings.global_config["plugins"]["data"][<plugin_id>]`` until the user clicks **Save** on the Settings page (same as other AB settings). After restart they load again with the rest of global settings.

### 3. A Settings chapter for those prefs

Register a chapter so users can edit prefs in the Settings sidebar:

```python
ctx.register_settings_chapter(
    f"{ctx.plugin_id}.settings",
    MyPluginSettingsChapter,  # thin subclass that closes over ctx.settings
    title="My Plugin",
)
```

Subclass `BaseSettingsChapter` and implement:

| Method | Role |
|--------|------|
| `get_current_state()` | Current widget values (for dirty detection) |
| `reset()` | Load widgets from `ctx.settings` (or defaults) |
| `set_settings()` | Write widgets into `ctx.settings` when the user saves Settings |

Define the UI class (e.g. `MySettingsChapter`) with constructor injection for `plugin_settings`, then in `activate` create a thin subclass (e.g. `MyPluginSettingsChapter`) that closes over `ctx.settings` and register that. Same pattern for pages that need `ctx.signals`. See Plugin Example (`settings_chapter.py` + `PluginExampleSettingsChapter` in `activate.py`).

**Do not** write to `activity_browser.app.settings` or `global_config` from a plugin — only `ctx.settings` and the chapter APIs above.

## Integration boundaries

Plugins **contribute alongside** Activity Browser’s base UI; v1 does not let you plug into base pages or panes directly.

### What v1 supports

| Mechanism | Use for |
|-----------|---------|
| **Your own page / pane** | UI that lives in a plugin tab or dock |
| **`register_action` + `register_menu_item`** | Commands under **Plugins → \<your plugin\>** |
| **`register_settings_chapter`** | Preferences under Settings |
| **Brightway** (`bw2data`, `bw2calc`, …) | Shared **domain** data — activities, databases, methods, calculation setups (same source base UI uses) |
| **`ctx.signals` (listen only)** | React to project, database, metadata, and other host events |
| **`sync()` on your pane** | Refresh plugin UI when the project changes (see Plugin Example) |
| **`ctx.settings`** | Namespaced plugin preferences |

### What v1 does **not** support

| Goal | Status |
|------|--------|
| Add a button or context-menu action to a **base pane** (e.g. Databases) | **Not supported** — base panes wire `app.actions.*` internally; there is no `register_pane_action` |
| Add items to core menus (Project, Database, View, …) | **Not supported** — only the **Plugins** menu tree |
| Read another page’s widget state, selection, or in-memory model | **Not supported** — no API to reach base page/pane instances |
| Register custom signals on the host bus | **Not supported** |

Need integration into base UI? Put the action under **Plugins → Your plugin** for now, or open a feature request for a future API extension (likely a new plugins API generation).

### Unsupported workarounds

Importing `activity_browser.app`, reaching `main_window`, or using `findChild` to read base UI may work briefly but is **unsupported**: it bypasses the public contract, breaks across AB releases, and can fail when base panes are recreated on project sync.

### Sharing data with base pages

Plugins and base pages see the **same Brightway project**, not each other’s Qt widgets. To show related information:

1. Read or write domain data through Brightway APIs.
2. Listen to `ctx.signals` and refresh your page/pane when relevant events fire.
3. Avoid coupling to base page classes or pane internals.

Example: a plugin can list databases via `bw2data` and react to `ctx.signals.database.written`; it cannot ask DatabasesPane which row the user highlighted unless AB adds a supported selection API later.
