---
title: Getting started
parent: Plugins
---
# Getting started with plugins
{: .fs-9 }

Build intuition by installing and exploring **Plugin Example**.
{: .fs-6 .fw-300 }

## Prerequisites

- Activity Browser 3 development install
- From the repo root: `pip install -e ./plugins/ab-plugin-example`

## Enable Plugin Example

1. Start Activity Browser  
2. Open **Settings → Plugins** (or **Plugins → Manage plugins…**)  
3. Select **Plugin Example**, enable it, **Save**  
4. Restart Activity Browser  

## Use the Plugins menu

Under **Plugins → Plugin Example** you can **Show example page** and **Show example pane**. The pane listens for project-change signals; the page echoes a namespaced greeting setting.

## Preferences

Settings also gains a **Plugin Example** chapter for the greeting preference (saved with Settings Save).

## Read the code

Open `plugins/ab-plugin-example/ab_example/activate.py` — each `register_*` call maps to what you saw in the UI. UI classes live in sibling modules (`page.py`, `pane.py`, …); contribution ids are in `ids.py`.

### Suggested layout for your own plugin

For a small plugin, use flat modules like Plugin Example. For a larger plugin, mirror Activity Browser’s `app/` layout (`pages/`, `panes/`, `actions/`, `settings/`, plus optional Brightway-only logic).

```text
my_plugin/
  __init__.py           # metadata; re-export activate
  activate.py           # wiring only
  ids.py
  page.py / pages/
  pane.py / panes/
  actions.py / actions/
  settings_chapter.py / settings/
```

## API version

Plugin Example declares `PLUGINS_API_VERSION = "1"` in `ab_example/__init__.py` — the plugins API generation it was written against. See [Plugins API version](../../docs/plugins/api-reference.md#plugins-api-version) for how compatibility is checked, when AB bumps the generation, and why backward-compatible extensions stay on `"1"`.

## Next steps

- [API reference](api-reference.md) — full `PluginContext` surface, [versioning](api-reference.md#plugins-api-version), and [integration boundaries](api-reference.md#integration-boundaries)  
- Scaffold your own package: declare `[project.entry-points."activity_browser.plugins"]`, set `PLUGINS_API_VERSION = "1"`, implement `activate(ctx)`
