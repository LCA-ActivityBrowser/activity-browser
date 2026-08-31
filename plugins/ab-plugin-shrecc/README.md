# SHRECC plugin for Activity Browser

Visual **SHRECC workflow** for Activity Browser: Configure → Create (action) → Inspect → Write.

Install in development:

```bash
pip install -e ./plugins/ab-plugin-shrecc
```

Enable under **Settings → Plugins**, restart AB, then **Plugins → Open SHRECC**.

Requires host APIs from the `plugins` branch (`protect_databases`, `after_database_write`, `run_blocking_operation`, `safe_bw_connection`).

## Plugin glossary

| Term | Summary |
|------|---------|
| **SHRECC workflow** | One closable tab: workflow project, Configure, Create action, Inspect, Write |
| **TYNDP scenario** | ENTSO-E storyline code for prospective mixes (not AB Scenario LCA) |
| **Plugin job** | In-flight Create or Write; at most one app-wide |
| **Project mismatch** | Workflow project ≠ currently open Brightway project |
| **Configuration mismatch** | Configure changed after last successful Create |

Canonical definitions: [`CONTEXT.md`](CONTEXT.md) in this package (moves with the plugin).

## Status

Core plugin: workflow shell (Configure → Create action → Inspect → Write), background Create, Write with overwrite confirm and metadata refresh. Stage tabs stay visible and disabled until gated; Inspect/Write enable after Create (Write disables again under configuration mismatch). Future stages (e.g. Analysis) should use the same always-visible, disabled-until-gated pattern.

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
6. **Configure:** years, countries, time range, background DB; set TYNDP scenario/climate year for prospective years. Use **Create** (bottom of Configure).
7. **Inspect:** opens after Create; review Mapping gaps, Inventory preview, Create log.
8. **Write:** set output database base name; review write plan; confirm overwrite if needed; write runs modally; check Databases pane for new inventories.

Optional: set **Settings → SHRECC → Data directory** for SHRECC cache location.

## Tests

```bash
pytest tests/plugins/test_shrecc_*.py tests/plugins/test_ab_shrecc.py -q
```

Fast unit tests cover `ShreccPluginController` gating and mocked create/write services. Integration smoke (`test_shrecc_integration.py`) exercises configure → create → write with mocked SHRECC and recorded host API calls.
