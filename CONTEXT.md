# Activity Browser — Domain Context

Canonical glossary and domain language for developers and AI agents. Prefer these terms over synonyms. Grow this file via `/grill-with-docs` / `/domain-modeling` when new terms stabilize.

Architecture decisions live in `docs/adr/`. Agent workflow and doc layout: `docs/agents/README.md`.

## Glossary

### Project

A Brightway2 workspace containing databases, methods, calculation setups, and parameters. Switching projects changes the active data context for the whole app (`app.signals.project`).

### Database

A named Brightway2 inventory database (activities and exchanges). In AB, databases appear in panes such as Databases / Database products; read-only vs writable state is tracked with settings and signals.

### Activity (process / node)

A unit process or transforming activity in a database. In the UI this is often opened as an **activity details** page. In signals/metadata, related concepts may appear as **node**.

### Exchange (flow / edge)

A flow between activities (processes) (technosphere) or from/to biosphere flows, with an amount and optional uncertainty/parameters. In signals, related updates may appear as **edge**. TBD: AB-wide exchanges should be renamed to flows.

### Product / reference product

The output of an activity that can be used as a functional flow in a calculation setup. Multifunctional activities may have multiple products; The functional_sqlite (bw-functional) backend distinguishes products and wastes. Product-outputs and waste-inputs are funcional flows. The revers combinations are non-functional flows. Further concepts (e.g. allocation) are defined in the  `bw-functional` / functional_sqlite code and documentation.

### Biosphere / elementary flow

Environmental or resource flows (emissions, resources) between processes (activities) and the environment (biosphere). Together they build the B-matrix. These flows are characterized by characterization factors (CF) within different LCIA methods. Distinct from technosphere exchanges between activities. ISO 14040 calls them elementary flows.

### Technosphere / intermediate flow

Flows (exchanges) between processes (activities) in the technosphere (man-made system). These together build the A-matrix. ISO 14040 calls them intermediate flows.

### Functional unit

The quantified output (or input in case of a waste treatment system) of the product system used as the reference for an LCA (the flow fullfilling the functional unit is also called reference flow). TBD: It is currently unclear if the best naming in the Calculation Setup should be functional unit or reference flow. 

### Calculation setup (CS)

A named set of functional unit(s) and LCIA method(s) used to run LCA / multi-LCA / Monte Carlo. Managed under calculation-setup UI and `app` actions. It can also additionaly include scenarios as a third element in the "Scenario" LCA mode. 

### LCIA method / impact category

A Life Cycle Impact Assessment method (characterization factors for elementary flows). In Brightway, methods are keyed tuples; AB exposes them in impact-category UI.

### Characterization factor (CF)

A factor that converts an elementary flow amount into an impact-category score for a given method.

### LCA / Multi-LCA

Life Cycle Assessment calculation (inventory + impact). Multi-LCA runs multiple functional units and/or methods; see `activity_browser/bwutils/multilca.py` and LCA results pages.

### Parameter

A named value or formula used to drive exchange amounts or scenarios. Parameter recalculation and Monte Carlo hooks live under `activity_browser/bwutils/parameters/`.

### Uncertainty

Statistical description of exchange (or parameter or CF) variability (`stats_arrays` types). UI preview helpers live under `activity_browser/bwutils/uncertainty.py` and related dialogs.

### Monte Carlo

Stochastic sampling of uncertain inputs to produce distributions of LCA results. Uncertainties can related to biosphere and technosphere flows, as well as to parameters and characterization factors. See `activity_browser/bwutils/montecarlo.py` and LCA results Monte Carlo UI.

### GSA (Global Sensitivity Analysis)

Analysis of how uncertain inputs drive output variance (e.g. SALib-based), based on Monte Carlo snapshots. See `activity_browser/bwutils/sensitivity_analysis.py`.

### Scenario LCA

An LCA calculation that also considers multiple scenarios for inventory data (based on the superstructure approach). See `activity_browser/bwutils/superstructure/`.

### Metadata store

Cached tabular metadata for fast UI search and display (`app.metadata` / `activity_browser.bwutils.metadata`). Synced via `app.signals.metadata` and related meta signals; tests often wait for the metadata loader.

### Signals (event bus)

`app.signals` (`ABSignals`) — primarily a bridge from Brightway/bw2data (blinker) events to Qt UI updates. Preferred path: action → Brightway/bwutils → bw signals → UI. See `docs/adr/0003-signals-event-bus.md`.

### Action

Command-style operation under `activity_browser/app/actions/` (menus, toolbars, context menus). Preferred place for Brightway-mutating user commands.

### Page / Pane

**Page:** main content view (`activity_browser/app/pages/`, based on `ui` abstracts). **Pane:** dockable side panel (`activity_browser/app/panes/`).

### Plugin

Extensibility mechanism for third-party AB features. **Architecture TBD** — do not invent API contracts; document here when redesigned.

## Synonyms to avoid (prefer glossary term)

| Avoid drifting to… | Prefer                                                                                   |
|---|------------------------------------------------------------------------------------------|
| “table of processes” | database / activity                                                                      |
| “flow” without kind | intermediate (technosphere) or elementary (biosphere) flow; exchanges is another synonym |
| “impact method” only | LCIA method / impact category (as used in UI)                                            |
| “global app settings file” ad hoc | `app.settings`                                                                           |
