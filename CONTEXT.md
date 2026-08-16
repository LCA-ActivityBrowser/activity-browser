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

### Functional flow

The exchange that expresses the purpose of a process: either a **product** output or a **waste** input. The reverse combinations (product input, waste output) are non-functional flows. Further concepts (e.g. allocation) are defined in the `bw-functional` / functional_sqlite code and documentation.
_Avoid_: reference flow (when meaning the process’s function rather than the LCA study’s functional unit)

### Product / reference product

A functional output of a process; can be used as a functional unit in a calculation setup. Multifunctional activities may have multiple products. On functional_sqlite, products are distinct nodes (`type=product`). On sqlite, a `processwithreferenceproduct` whose production amount is non-negative plays this role.
_Avoid_: output (alone), good

### Waste

A functional input of a process (waste treatment): the process exists to take in that waste. On functional_sqlite, wastes are distinct nodes (`type=waste`). On sqlite, a `processwithreferenceproduct` whose production amount is negative plays this role.
_Avoid_: waste treatment (when meaning the flow itself rather than the treating process)

### Biosphere / elementary flow

Environmental or resource flows (emissions, resources) between processes (activities) and the environment (biosphere). Together they build the B-matrix. These flows are characterized by characterization factors (CF) within different LCIA methods. Distinct from technosphere exchanges between activities. ISO 14040 calls them elementary flows.

### Technosphere / intermediate flow

Flows (exchanges) between processes (activities) in the technosphere (man-made system). These together build the A-matrix. ISO 14040 calls them intermediate flows.

### Functional unit

The quantified output (or input in case of a waste treatment system) of the product system used as the reference for an LCA (the flow fullfilling the functional unit is also called reference flow). TBD: It is currently unclear if the best naming in the Calculation Setup should be functional unit or reference flow. 

### Calculation setup (CS)

A named set of functional unit(s) and LCIA method(s) used to run LCA / multi-LCA / Monte Carlo. Managed under calculation-setup UI and `app` actions. It can also additionaly include scenarios as a third element in the "Scenario" LCA mode. The CS page always opens in **Standard** mode; switching to **Scenario** mode may reload persisted scenario files (with a loading indication). Scenario file paths, combine mode, and the included scenario-combinations set may be stored on the CS.

### LCIA method / impact category

A Life Cycle Impact Assessment method (characterization factors for elementary flows). In Brightway, methods are keyed tuples; AB exposes them in impact-category UI.

### AB impact-category file (AB LCIA format)

Activity Browser’s multi–impact-category interchange for import/export: characterization factors plus per–impact-category unit and description. Method keys and elementary-flow identities use `::` (variable-length Brightway tuples / categories). Excel uses sheets `CFs` and `Impact categories`; CSV uses a sibling pair `*.cfs.csv` + `*.metadata.csv`. Distinct from ecoinvent’s LCIA implementation workbook (fixed three-part names; separate name/compartment/subcompartment columns) and from the **bw2io impact-category file**.
_Avoid_: Indicators sheet (when meaning AB’s impact-category metadata table), AB ecoinvent format

### bw2io impact-category file (bw2io LCIA format)

bw2io’s Excel/CSV LCIA CF template: **one impact category per CF file/sheet** (`name`, `categories` with `::`, `amount`, optional uncertainty). AB may add a `metadata` sheet (xlsx) or `metadata.csv` sidecar for method/unit/description/`filename`; stock bw2io only needs the CF table.
_Avoid_: one-shot, bw2io native (as a product name), AB impact-category file

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

### Scenario name

The string identifier of a scenario column in a scenario difference file (or in a combined scenario table). Always a string — file importers coerce numeric-looking headers (e.g. Excel `2025`) with `str(...)`. When scenarios from multiple files are combined (product), the combined scenario name is the file-order join of the parts with ` | ` (e.g. `A` and `X` → `A | X`). _Avoid_: scenario header (as a typed value), scenario label when meaning the column identity.

### Scenario-combinations list

The list of product-combined scenario names from two or more loaded scenario difference files (e.g. `A | X`), each with an include checkbox. Shown beside the per-file scenario lists in the calculation setup when 2+ files are loaded under Combine. Together with per-file scenario checkboxes it supports coarse (row/column/slice) and fine (cell) inclusion. Under **Extend**, there is no combinations list: inclusion is by shared scenario name, and checkboxes for the same name stay in sync across files. _Avoid_: scenario-selection-matrix (deferred 2D editor), SS-matrix, combiner matrix.

### Metadata store

Cached in-memory table of activity/process fields for fast UI search and display (`app.metadata` / `activity_browser.bwutils.metadata`). Index is `(database, code)`; column `id` is the Brightway datapackage id. Synced via `app.signals.metadata` and related meta signals; tests often wait for the metadata loader.

**Read path:** prefer the store for names, products, locations, units, databases, and other stored fields. Do not query `ActivityDataset` or `bd.get_node` per row when the store already has the id or key. **Write path:** mutate via Brightway APIs (actions); the store updates from bw signals. Fallback to Brightway only for missing rows, fields the store does not keep, or when a live activity proxy is required.
_Avoid_: fetching display metadata from SQLite when the MetaDataStore is available

### Signals (event bus)

`app.signals` (`ABSignals`) — primarily a bridge from Brightway/bw2data (blinker) events to Qt UI updates. Preferred path: action → Brightway/bwutils → bw signals → UI. See `docs/adr/0003-signals-event-bus.md`.

### Action

Command-style operation under `activity_browser/app/actions/` (menus, toolbars, context menus). Preferred place for Brightway-mutating user commands.

### Page / Pane

**Page:** main content view (`activity_browser/app/pages/`, based on `ui` abstracts). **Pane:** dockable side panel (`activity_browser/app/panes/`).

### Plugin

Extensibility mechanism for third-party AB features. **Architecture TBD** — do not invent API contracts; document here when redesigned.

### Contribution tree

A hierarchical, acyclic breakdown of LCA impact by upstream supplier, produced by priority-first graph traversal (`SameNodeEachVisitGraphTraversal`). Each node carries a **cumulative impact** (its own direct emissions plus all upstream) and a **direct impact** (its own biosphere flows only). The root is the functional unit; children are direct technosphere suppliers, recursed up the supply chain. Shown in AB as a `QTreeView` with one row per traversed node, in the **Tree** tab of the LCA Results page. Nodes are calculated lazily on expand; the **adjust policy** controls how far the Adjust control walks the tree.
_Avoid_: supply-chain tree, upstream tree (use contribution tree in AB UI; "upstream tree" is the OpenLCA term for the same concept)

### Tier (contribution-tree depth)

The distance from the functional unit in the contribution tree. The functional unit is tier 0; its direct suppliers are tier 1; their suppliers are tier 2; and so on. Not to be confused with the sequential first-tier substitution approach used in the (disabled) `FirstTierContributionsTab`.
_Avoid_: level, depth (fine internally but use "tier" in UI labels and the Tier column)

### Cumulative impact

The absolute LCA score attributable to a contribution-tree node, including all its upstream suppliers (`node.cumulative_score`). Shown as a column in the contribution tree table and as wedge size in the sunburst plot. The **Cumulative impact (%)** column expresses this as a fraction of the total LCA score.
_Avoid_: upstream total, total result, cumulative score (use cumulative impact in UI labels)

### Direct impact

The absolute LCA score from a node's own biosphere flows only, excluding its upstream (`node.direct_emissions_score`). Shown as a separate column in the contribution tree table.
_Avoid_: direct contribution, direct emissions score (use direct impact in UI labels)

### Direct-impact coverage

Two related ratios, both Σ(direct impact) / |total score| (equivalent to summing the **Direct impact (%)** column):

- **Shown (footer):** only rows currently visible in the tree (ancestors expanded). Updates on expand/collapse.
- **Calculated (footer):** all nodes discovered by graph traversal (excluding the virtual demand root). The Cumulative expand “(target X% — not reached)” note uses this when even the full calculated graph stays below the target.
- **Cumulative expand display set:** largest-first by remaining upstream (|cumulative| − |direct|). Nodes that are already almost entirely direct are not auto-opened. When a node is opened, children are added largest-first and stop once Σ(direct of included) reaches the target %. Leftover siblings stay out of the model (manual expand can still reveal them).

Footer format: `Shown: N nodes, Y% of direct impacts, max tier T | Calculated: Z nodes, A% of direct impacts, max tier U`.
_Avoid_: traversal coverage, score coverage (unless clearly meaning this ratio)

### Path impact

The cumulative impact of a contribution-tree node as a share of the total LCA score — i.e. how much of the result flows through that supply-chain path. Shown as **Cumulative impact (%)**. The **Individual path impact** adjust policy auto-opens nodes at/above a chosen path % only while a child at/above that % remains (terminal high-path nodes stay collapsed); under opened nodes it lists all discovered siblings. Only the engine traversal **cutoff** omits smaller branches from calculation.
_Avoid_: individual impact (alone), branch score

### Adjust policy

How far the **Adjust to** control calculates and visually opens the contribution tree. Modes: **Tier** (open down to a given tier), **Individual path impact** (keep expanding while path impact ≥ X% continues into a child; list all discovered children under opened nodes; leave terminal ≥ X% rows collapsed), **Cumulative impact** (largest-first from the reference flow until the **display set**’s direct-impact coverage reaches a target %, capped below 100% — does not open every previously calculated node). Distinct from a later optional **display filter** that only hides already-calculated rows. Open branches and which rows are in the tree are remembered per RF / impact category / scenario / cutoff when switching selections in the Tree tab.
_Avoid_: cutoff (alone — ambiguous with Process Contributions and engine traversal cutoff); expand policy (legacy UI label — use adjust policy)

### Plot–tree linking

Clicking a segment in a contribution-tree plot selects the corresponding row and expands or collapses that branch in the tree (or the parent row when the segment is an aggregate band). **Terminal** segments (no downstream suppliers after traversal) are **expand-only** from the plot — one expand attempt if collapsed, otherwise no-op. Non-terminal segments toggle expand/collapse. The plot refreshes to match the visible tree.
_Avoid_: interactive chart (alone — specify plot–tree linking)

### Plot aggregation

Plot-only rollup of **sibling** segments under the same parent by a metadata field (Product, Process, Location, Unit, Database). Band width and direct-impact tint use summed impacts; the tree table is unchanged.
_Avoid_: aggregate the contribution tree (alone — plot aggregation is plot-only in v1)

### Flow amount

The scaled technosphere demand for a contribution-tree node (`node.supply_amount`), expressed in the reference product's unit. Shown in the "Flow amount" and "Unit" columns of the contribution tree table.
_Avoid_: required amount, supply amount (use flow amount in UI labels)

## Synonyms to avoid (prefer glossary term)

| Avoid drifting to… | Prefer                                                                                   |
|---|------------------------------------------------------------------------------------------|
| “table of processes” | database / activity                                                                      |
| “flow” without kind | intermediate (technosphere) or elementary (biosphere) flow; exchanges is another synonym |
| “impact method” only | LCIA method / impact category (as used in UI)                                            |
| “Indicators” (AB LCIA metadata sheet/file) | Impact categories (Excel sheet) / `.metadata.csv` (AB CSV sidecar) |
| “one-shot” / “bw2io native” (LCIA file) | bw2io impact-category file |
| “global app settings file” ad hoc | `app.settings`                                                                           |
