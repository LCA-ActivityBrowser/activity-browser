# Domain data flows through Brightway signals into Qt (`app.signals`)

UI components must stay loosely coupled to inventory and project changes. Activity Browser’s **prevailing and preferred** path is: **user → action → Brightway / bwutils → bw2data (blinker) signals → `ABSignals` bridge → Qt UI refresh**. `app.signals` (`activity_browser/app/signalling.py`) is primarily that bridge, not a free-form UI-to-UI command bus.

**Do:** mutate data via Brightway APIs (usually from actions); let UI **listen** to bridged signals (`node`, `edge`, `database`, `project`, `meta`, `parameter`, …). **Don’t:** have UI emit domain/data signals to drive other UI after local edits — that bypasses the source of truth.

**Allowed exceptions:** (1) manual `app.signals.*.emit` when upstream does not signal yet (often paired with a `mod/` or signalling patch — prefer fixing upstream later); (2) a small set of **AB-only session/UI** signals that are not dataset mutations (e.g. `database_selected`, `database_read_only_changed`, `monte_carlo_finished`, `plugin_selected`); (3) ordinary local widget signals that never leave the widget/page.
