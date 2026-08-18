# Separate `ui/`, `app/`, and `bwutils/` layers

Activity Browser splits presentation and LCA logic so reusable Qt widgets stay free of app singletons, while Brightway-facing orchestration stays testable and findable. **`ui/`** holds application-agnostic Qt components; **`app/`** holds pages, panes, actions, and dialogs that depend on `app.signals` / settings / metadata and perform Brightway mutations (especially in actions); **`bwutils/`** holds Brightway/scientific helpers without Qt UI. Place new code with: Brightway-only → `bwutils/`; no app init needed → `ui/`; otherwise → `app/`.

## Future work

Demand identity for `functional_sqlite` (process datapackage ids vs product ids in `LCA` / `redo_lci`) is an Activity Browser stopgap in `bwutils/lca_inputs.py` (Tree and Sankey). MultiLCA, Monte Carlo, and GSA still prepare demand independently. This mapping should move to a central helper, preferably **bw_functional** itself — not a new AB layering rule. Amend this ADR (or replace the stopgap) when that upstream API exists.
