# SHRECC plugin for Activity Browser

Visual **SHRECC workflow** for Activity Browser: Configure → Create (action) → Inspect → Write, plus a plugin-level **SHRECC Explorer** tab for browsing local electricity datasets before Create.

Install in development:

```bash
pip install -e /path/to/shrecc_explorer
pip install -e "./plugins/ab-plugin-shrecc[explorer]"
```

The plugin’s **`explorer`** extra pulls in Brightway-free **`shrecc-explorer`** (Streamlit entry `shrecc-explorer`). Install from the explorer repo until it is published.

Enable under **Settings → Plugins**, restart AB, then **Plugins → Open SHRECC**.

Requires host APIs (`protect_databases`, `run_blocking_operation`, `safe_bw_connection`). Database writes must emit Brightway `on_database_write` (e.g. `signal=True`) so the host Metadata store refreshes after the worker exits.

## Plugin glossary

| Term | Summary |
|------|---------|
| **SHRECC Explorer** | Fixed top-level tab (sibling to workflows): explore local datasets; Prepare; optional Open in browser |
| **SHRECC workflow** | One closable tab: workflow project, Configure, Create action, Inspect, Write |
| **Data directory** | Shared Settings path for SHRECC cache and explorer exports (`…/explorer/exports`) |
| **Explorer prepare** | Explicit export of cache → explorer NetCDF (Plugin job) |
| **TYNDP scenario** | ENTSO-E storyline code for prospective mixes (not AB Scenario LCA) |
| **Plugin job** | In-flight Create, Write, or Explorer prepare; at most one app-wide |
| **Project mismatch** | Workflow project ≠ currently open Brightway project |
| **Configuration mismatch** | Configure changed after last successful Create |

Canonical definitions: [`CONTEXT.md`](CONTEXT.md) in this package (moves with the plugin). Architecture: [`docs/adr/`](docs/adr/).

## Status

Core plugin: workflow shell (Configure → Create action → Inspect → Write), background Create, Write with overwrite confirm. Stage tabs stay visible and disabled until gated; Inspect/Write enable after Create (Write disables again under configuration mismatch).

**SHRECC Explorer** embeds the standalone Streamlit explorer (Country / Cross-country / Storage) in a WebEngine view when explorer-ready NetCDFs exist under the data directory. It is not gated on Create and does not use Create in-memory results.

## SHRECC Explorer (quick use)

1. Set **Settings → SHRECC → Data directory** to the same root Create uses (or leave empty for SHRECC’s default).
2. Open **Plugins → Open SHRECC** → **Explorer** tab.
3. If SHRECC cache is present but no NetCDF yet, click **Prepare** (blocked while Create/Write runs).
4. When datasets are ready, the embedded explorer starts (or use **Open in browser** for a full window — same local server).

Explorer-ready files live under `<data_dir>/explorer/exports/`; comparison summaries under `<data_dir>/explorer/prepared/`.

## Manual end-to-end demo (real SHRECC)

CI tests use a **mocked** `NewDatabase` and do not download Energy Charts or TYNDP data. For a real run:

1. **Host branch:** Activity Browser on `plugins` (or merged), SHRECC plugin on `shrecc`.
2. **Install SHRECC** and **shrecc-explorer** from your local trees (editable):

   ```bash
   pip install -e /path/to/shrecc
   pip install -e /path/to/shrecc_explorer
   pip install -e ./plugins/ab-plugin-shrecc
   ```

3. **Brightway project:** Open a project with a suitable background database (e.g. ecoinvent cutoff or premise DB for TYNDP years).
4. **Enable plugin** in Settings → Plugins; restart AB.
5. **Plugins → Open SHRECC** — **Explorer** plus one workflow tab open by default.
6. **Configure:** years, countries, time range, background DB; set TYNDP scenario/climate year for prospective years. Use **Create** (bottom of Configure).
7. **Inspect:** opens after Create; review Mapping gaps, Inventory preview, Create log.
8. **Write:** set output database base name; review write plan; confirm overwrite if needed; write runs modally; check Databases pane for new inventories.

Optional: set **Settings → SHRECC → Data directory** for SHRECC cache location (shared with Explorer).

## Tests

```bash
pytest tests/plugins/test_shrecc_*.py tests/plugins/test_ab_shrecc.py -q
```

Fast unit tests cover `ShreccPluginController` gating, explorer session discovery/Prepare job lock, and mocked create/write services. Integration smoke (`test_shrecc_integration.py`) exercises configure → create → write with mocked SHRECC and recorded host API calls.
