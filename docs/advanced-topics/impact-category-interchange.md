# Impact category import and export

Activity Browser supports three spreadsheet interchange styles for **impact categories** (Brightway LCIA methods).

## Formats

### AB impact-category file (recommended default)

Multi–impact-category file with self-describing metadata and variable-length method names.

- **Excel:** sheets `CFs` and `Impact categories` (templates also include `README`)
- **CSV pair:** `*.cfs.csv` and `*.metadata.csv`

| Sheet / file | Columns |
|---|---|
| CFs / `*.cfs.csv` | `method`, `flow`, `amount`, optional uncertainty fields |
| Impact categories (xlsx) / `*.metadata.csv` | `method`, `unit`, `description` |

- `method` and `flow` use `::` (e.g. `My method::climate change::GWP100`, `Ammonia::air::unspecified`)
- Uncertainty columns: `uncertainty type`, `loc`, `scale`, `shape`, `minimum`, `maximum`, `negative`

Menu: **Impact categories → Import → From AB LCIA file (.xlsx/.csv)…** / **Export → To AB LCIA file (.xlsx/.csv)…**

### bw2io impact-category file

Compatible with bw2io’s Excel/CSV LCIA CF table (`name`, `categories` with `::`, `amount`, optional uncertainty): **one impact category per CF file**.

- **Excel:** CF sheet + AB `metadata` sheet (`filename`, `method`, `unit`, `description`) used to prefill the import dialog
- **CSV:** one CF file per impact category + shared `metadata.csv` sidecar (`filename` matches the CF file name when several rows exist)
- Exported file names join method-tuple parts with `__` (not `::`, which is illegal on Windows) and replace other forbidden characters with `-`

Stock bw2io only needs the CF table; AB reads metadata when present and always shows a confirmation dialog. You can multi-select several Excel/CSV files in one import; shared CSV `metadata.csv` rows are matched by `filename`.

Menu: **Impact categories → Import → From bw2io LCIA file (.xlsx/.csv)…** / **Export → To bw2io LCIA file (.xlsx/.csv)…**

### ecoinvent LCIA Implementation Excel

Vendor multi-method workbook (`CFs` + `units` / `Indicators`). Method names are three parts (`method` / `category` / `indicator`); flows use name / compartment / subcompartment columns. Here **Indicators** is ecoinvent’s sheet name (not AB’s metadata table).

Menu: **Impact categories → Import → From ecoinvent Excel…**

## Templates

**Impact categories → Get template…** copies starters from `activity_browser/templates/impact-categories/`. AB impact-category file is listed first (default).

## Import behaviour (AB and bw2io file imports)

- Choose the biosphere database used for linking
- Multi–impact-category conflicts: skip existing / overwrite (with confirm) / rename with a namespace prefix; optional per-conflict rename table
- Single bw2io impact-category file name conflict: overwrite (with confirm), edit name, or cancel
- Unlinked characterization factors: dialog shows linked and unlinked counts; cancel, export unmatched list, or drop unlinked (no automatic biosphere creation)
- Long-running load, link, write, and export steps show a progress dialog with **Cancel**. Cancel stops the job. For import write, methods **created** in that run are rolled back so they do not remain in the project. **Overwrite runs are different:** if cancel happens after an existing impact category was already removed/replaced, that category may stay deleted or partially updated (the UI warns about this when overwrite is chosen). Full overwrite undo is out of scope for v1.

## Export behaviour

Menu export uses the current Impact categories pane selection. If nothing is selected (or the pane cannot be resolved), you are asked whether to export all impact categories. Export also shows a progress dialog while reading methods and writing files.