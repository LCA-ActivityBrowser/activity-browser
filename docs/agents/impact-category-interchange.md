# Impact-category interchange (agent notes)

Canonical user docs: [`docs/advanced-topics/impact-category-interchange.md`](../advanced-topics/impact-category-interchange.md).

Glossary in root `CONTEXT.md`: **AB impact-category file**, **bw2io impact-category file**. Prefer “impact category” / “LCIA method”; avoid “Indicators” for AB metadata and avoid “one-shot” / “bw2io native”.

Implementation seam: `activity_browser.bwutils.impact_categories` — `ab_lcia_file` / `bw2io_lcia_file` / `ecoinvent_lcia` / `common`; `ABLCIAImporter` links and writes prepared datasets (fed by AB or bw2io loaders).

UI: one ABAction per file under `app.actions.method` (`method_import_*`, `method_export_*`, `method_get_template`). Action-specific dialogs and worker threads live in those same modules (repo convention). Shared sticky-cancel progress starter is `app.dialogs.run_thread_with_progress` (`ABProgressDialog` remains in `ui.dialogs`). Menu export selection is `live_impact_category_selection()` / `resolve_methods_for_export()` on the Impact categories pane.

AB CSV pair suffixes: `.cfs.csv` + `.metadata.csv` (Excel sheet name remains **Impact categories**). Do not use “Indicators” for AB metadata.

Templates: `activity_browser/templates/impact-categories/`.
