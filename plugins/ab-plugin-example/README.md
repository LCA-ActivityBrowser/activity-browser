# Plugin Example

Example plugin for Activity Browser 3. It demonstrates every v1 contribution
point (`PluginContext` registration) and is **not** a real LCA analysis tool.

## Install

```bash
pip install -e ./plugins/ab-plugin-example
```

Enable **Plugin Example** under Settings → Plugins, **Save**, then restart Activity Browser.

## Package layout

```text
ab_example/
  __init__.py           # PLUGINS_API_VERSION, PLUGIN_DISPLAY_NAME
  activate.py           # activate(ctx) — registration wiring only
  ids.py                # contribution id constants
  page.py               # ExamplePage
  pane.py               # ExamplePane
  actions.py            # menu actions
  settings_chapter.py   # Settings chapter
```

Start with `activate.py` to see what this plugin adds to Activity Browser.

## Entry point

- Entry point name / `plugin_id`: `ab_example`
- Display name: Plugin Example
- `PLUGINS_API_VERSION = "1"` in `ab_example/__init__.py` — plugins API generation this package targets (see [versioning docs](../../docs/plugins/api-reference.md#plugins-api-version))
