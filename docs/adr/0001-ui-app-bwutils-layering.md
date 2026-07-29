# Separate `ui/`, `app/`, and `bwutils/` layers

Activity Browser splits presentation and LCA logic so reusable Qt widgets stay free of app singletons, while Brightway-facing orchestration stays testable and findable. **`ui/`** holds application-agnostic Qt components; **`app/`** holds pages, panes, actions, and dialogs that depend on `app.signals` / settings / metadata and perform Brightway mutations (especially in actions); **`bwutils/`** holds Brightway/scientific helpers without Qt UI. Place new code with: Brightway-only → `bwutils/`; no app init needed → `ui/`; otherwise → `app/`.
