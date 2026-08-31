# SHRECC plugin for Activity Browser

Visual **SHRECC workflow** for Activity Browser: configure → create & inspect → write Brightway databases.

Install in development:

```bash
pip install -e ./plugins/ab-plugin-shrecc
```

Enable under **Settings → Plugins**, restart AB, then **Plugins → SHRECC → Open SHRECC**.

## Plugin glossary

Domain terms for this plugin (full definitions in `.scratch/shrecc-plugin/spec.md` §Plugin glossary):

| Term | Summary |
|------|---------|
| **SHRECC workflow** | One closable tab: bound Project, configuration, optional create results, optional write |
| **TYNDP scenario** | ENTSO-E storyline code for prospective mixes (not AB Scenario LCA) |
| **Plugin job** | In-flight `create()` or `write()`; at most one app-wide |
| **Project stale** | Workflow project ≠ current Brightway project |
| **Inspect stale** | Configure changed after last successful `create()` |

## Status

Core shell (ticket 13): workflow tabs, stage placeholders, settings `data_dir`. Configure/create/write stages follow in later tickets.
