# SHRECC plugin for Activity Browser

Visual **SHRECC workflow** for Activity Browser: configure → create & inspect → write Brightway databases.

Install in development:

```bash
pip install -e ./plugins/ab-plugin-shrecc
```

Enable under **Settings → Plugins**, restart AB, then **Plugins → Open SHRECC**.

Requires host APIs from the `plugins` branch (`protect_databases`, `after_database_write`, `run_blocking_operation`).

## Plugin glossary

| Term | Summary |
|------|---------|
| **SHRECC workflow** | One closable tab: bound Project, configuration, optional create results, optional write |
| **TYNDP scenario** | ENTSO-E storyline code for prospective mixes (not AB Scenario LCA) |
| **Plugin job** | In-flight `create()` or `write()`; at most one app-wide |
| **Project stale** | Workflow project ≠ current Brightway project |
| **Inspect stale** | Configure changed after last successful `create()` |

Full definitions: `.scratch/shrecc-plugin/spec.md` §Plugin glossary.

## Status

Core plugin (tickets 13–16): workflow shell, Configure stage, background create + inspect panels A–D, Write stage with overwrite confirm and metadata refresh.

## Manual end-to-end demo (real SHRECC)

CI tests use a **mocked** `NewDatabase` and do not download Energy Charts or TYNDP data. For a real run:

1. **Host branch:** Activity Browser on `plugins` (or merged), SHRECC plugin on `shrecc`.
2. **Install SHRECC** from your local develop tree (editable):

   ```bash
   pip install -e /path/to/shrecc
   pip install -e ./plugins/ab-plugin-shrecc
   ```

3. **Brightway project:** Open a project with a suitable background database (e.g. ecoinvent cutoff or premise DB for TYNDP years).
4. **Enable plugin** in Settings → Plugins; restart AB.
5. **Plugins → Open SHRECC** — one workflow tab opens by default.
6. **Configure:** years, countries, time range, background DB, output name; set TYNDP scenario/climate year for prospective years.
7. **Create & inspect:** Create runs in the background; review summary, mapping gaps, inventory preview, log.
8. **Write:** Confirm overwrite if needed; write runs modally; check Databases pane for new inventories.

Optional: set **Settings → SHRECC → Data directory** for SHRECC cache location.

## Tests

```bash
pytest tests/plugins/test_shrecc_*.py tests/plugins/test_ab_shrecc.py -q
```

Fast unit tests cover `ShreccPluginController` gating and mocked create/write services. Integration smoke (`test_shrecc_integration.py`) exercises configure → create → write with mocked SHRECC and recorded host API calls.
