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
_Avoid_: the functional flow refers to one or several flows in the context of a specific process; it is not the same as the reference flow or functional unit 

### Reference flow
This is the flow for which an LCA calculation is done in the Calculation Setup (upper section). It defines the output of a product system (or input to in case of waste treatment). It can be largely seen as a synonym for functional unit. We prefer the term reference flow in the Calculation Setup as not every flow listed there always needs to be the functional unit of the LCA a practitioner is conducting.

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

The quantified output (or input in case of a waste treatment system) of the product system used as the reference for an LCA (the flow fullfilling the functional unit is also called reference flow). For the calculation setup, it is better to use reference flows as not all flows listed there have to be functional units.

### Calculation setup (CS)

A named set of reference flow(s) and impact categories used to run LCA / multi-LCA / Monte Carlo. Managed under calculation-setup UI and `app` actions. It can also additionaly include scenarios as a third element in the "Scenario" LCA mode. The CS page always opens in **Standard** mode; switching to **Scenario** mode may reload persisted scenario files (with a loading indication). Scenario file paths, combine mode, and the included scenario-combinations set may be stored on the CS.

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

Life Cycle Assessment calculation (inventory + impact). Multi-LCA runs multiple reference flows and/or impact categories; see `activity_browser/bwutils/multilca.py` and LCA results pages.

### Parameter

A named value or formula used to drive flow amounts or scenarios. Parameter recalculation and Monte Carlo hooks live under `activity_browser/bwutils/parameters/`.

### Parameterized flow

A flow whose amount is given by a formula (optionally using parameters). The Parameters page lists them under **Parameterized Flows**. Recalculation and Monte Carlo use Brightway’s `ParameterizedExchange` index, which is keyed by activity-parameter group.
_Avoid_: parameterized exchange (when meaning this concept or the UI section)

### Uncertainty

Statistical description of flow, parameter, or characterization-factor variability. Monte Carlo samples this description. A lognormal uncertainty on a flow may be derived from an applied pedigree.
_Avoid_: treating stored pedigree scores as the sampled input

### Pedigree

Five 1–5 data-quality scores on a flow (reliability, completeness, temporal correlation, geographical correlation, further technological correlation). Together with basic uncertainty they are a stored recipe for the **spread** of a lognormal uncertainty (not its central value). The recipe is not applying when the uncertainty edit opens; applying it — when the user chooses to and confirms — sets that lognormal from the recipe; inspecting scores or cancelling does not. Switching to another uncertainty, or removing uncertainty, leaves the recipe stored so it can be applied again. The recipe can be cleared in that same edit (confirmed on OK) without changing the current uncertainty unless pedigree is also being applied. When present, the scores are shown with the flow’s uncertainty (not as a separate table column). Not used on parameters or characterization factors.
_Avoid_: pedigree matrix (when meaning these scores — that name is the factor table); data quality indicators (when meaning this pedigree); treating an unapplied pedigree as the current uncertainty

### Basic uncertainty

The extra lognormal spread assumed even when all pedigree scores are 1. Part of the pedigree recipe; not sampled on its own. Default is 1 when unset. When the current uncertainty is lognormal and scores exist, it is inferred from that scale and the scores so the recipe matches; if the scale is tighter than the scores alone, inference is not used (default 1). An inferred value is not stored until the user saves the pedigree recipe.
_Avoid_: sample size (the unused sixth ecoinvent pedigree number); treating this as a sixth 1–5 score

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

A hierarchical, acyclic breakdown of LCA impact by upstream supplier, produced by priority-first graph traversal (`SameNodeEachVisitGraphTraversal`). Each node carries a **cumulative impact** (its own direct emissions plus all upstream) and a **direct impact** (its own biosphere flows only). The root is the reference flow; children are direct technosphere suppliers, recursed up the supply chain. Shown in AB as a table (`QTreeView`) plus plots on the **Tree** tab of the LCA Results page. Nodes are calculated lazily on expand; the **adjust policy** controls how far the Adjust control walks the tree.
_Avoid_: supply-chain tree, upstream tree (use contribution tree in AB UI; "upstream tree" is the OpenLCA term for the same concept); calling the Tree-tab node-link plot “Sankey”

### Tier (contribution-tree depth)

The distance from the reference flow in the contribution tree. The reference flow is tier 0; its direct suppliers are tier 1; their suppliers are tier 2; and so on. Not to be confused with the sequential first-tier substitution approach used in the (disabled) `FirstTierContributionsTab`.
_Avoid_: level, depth (fine internally but use "tier" in UI labels and the Tier column)

### Cumulative impact

The absolute LCA score attributable to a contribution-tree node, including all its upstream suppliers (`node.cumulative_score`). Shown as a column in the contribution tree table and as wedge size in the sunburst plot. The **Cumulative impact (%)** column expresses this as a fraction of the total LCA score.
_Avoid_: upstream total, total result, cumulative score (use cumulative impact in UI labels)

### Direct impact

The absolute LCA score from a node's own biosphere flows only, excluding its upstream (`node.direct_emissions_score`). Shown as a separate column in the contribution tree table.
_Avoid_: direct contribution, direct emissions score (use direct impact in UI labels)

### Direct-impact coverage

Two related ratios, both Σ(direct impact) / |total score| (equivalent to summing the **Direct impact (%)** column):

- **Shown (footer):** only rows currently visible in the tree (ancestors expanded), or unique processes in the Sankey **display set**. Updates on expand/collapse.
- **Calculated (footer):** all nodes discovered by graph traversal (excluding the virtual demand root). On the Sankey, count **unique processes** in the calculated graph, not extra NNEV visits of the same process. The Cumulative expand “(target X% — not reached)” note uses this when even the full calculated graph stays below the target.
- **Cumulative expand display set:** largest-first by remaining upstream (|cumulative| − |direct|). When a node is opened, children that raise coverage are added largest-direct first until Σ(direct of included) reaches the target %. Zero-direct siblings are not listed just because coverage is stuck — only the next remaining-upstream hop (then that hop is opened before leftover siblings). A leftover 0-direct market beside a sibling that already adds direct impact (and still has more remaining upstream) stays hidden; a parent that already has a direct-impact child plus one remaining-upstream hop does not list extra 0-direct siblings. Leftover siblings stay out of the model (manual expand or **Show all** can still reveal them). Do not skip “mostly direct” nodes with a separate remaining-upstream ratio; Cumulative Adjust stops at the coverage target or the engine **cutoff**. On the Sankey, coverage and remaining use solved-inventory directs per unique process (same values as the boxes), not NNEV visit-level directs.

Footer format: `Shown: N nodes, Y% of direct impacts, max tier T | Calculated: Z nodes, A% of direct impacts, max tier U`. On the Sankey, “nodes” are unique processes.
_Avoid_: traversal coverage, score coverage (unless clearly meaning this ratio)

### Path impact

The cumulative impact of a contribution-tree node as a share of the total LCA score — i.e. how much of the result flows through that supply-chain path. Shown as **Cumulative impact (%)**. The **Individual path impact** adjust policy auto-opens nodes at/above a chosen path % only while a child at/above that % remains (terminal high-path nodes stay collapsed); siblings below that % are hidden. **Show all** (footer) draws every calculated node. Only the engine traversal **cutoff** omits smaller branches from calculation.
_Avoid_: individual impact (alone), branch score

### Adjust policy

How far the **Adjust to** control calculates and visually opens the **contribution tree** or **Sankey plot**. Modes: **Tier** (open down to a given tier), **Individual path impact** (keep expanding while path impact ≥ X% continues into a child; hide siblings below X%; leave terminal ≥ X% rows collapsed), **Cumulative impact** (largest-first from the reference flow until the **display set**’s direct-impact coverage reaches a target %, capped below 100% — does not open every previously calculated node). The calculated graph only grows; a tighter Adjust rebuilds the display set and may hide processes that stay calculated. **Show all** (footer, next to Calculated) draws the full calculated graph and is disabled when nothing is hidden. Adjust continues that graph. Switching reference flow, impact category, scenario, or cutoff starts a new calculated graph at the reference flow (tier 1); click **Adjust** to apply the current policy — do not inherit the previous selection’s Adjust walk. The engine cutoff is baked into which edges exist: lowering it (more branches) requires a new traversal; raising it currently also starts a new graph, even though a tighter cutoff could in principle filter the existing one. If the calculated graph already satisfies the policy, only the display set is rebuilt. Distinct from a later optional **display filter** that only hides already-calculated rows. Open branches and which rows are in the tree are remembered per RF / impact category / scenario / cutoff when switching selections in the Tree tab. The Sankey remembers its calculated graph the same way.
_Avoid_: cutoff (alone — ambiguous with Process Contributions and engine traversal cutoff); expand policy (legacy UI label — use adjust policy)

### Plot–tree linking

Clicking a segment or node in a contribution-tree plot selects the corresponding row and expands or collapses that branch in the table (or the parent row when the target is an aggregate). **Terminal** nodes (no further suppliers **after that visit has been traversed**) are **expand-only** from the plot — one expand attempt if collapsed, otherwise no-op. An untraversed visit is not terminal. Non-terminal nodes toggle expand/collapse. The plot refreshes to match the visible table. On the **tree plot** and **Sankey plot**, a triangle means a click would change what is shown (expand hidden or not-yet-traversed unique-process suppliers, or collapse currently shown ones). Right-click **Open process** opens **Activity Details** for that process (same command as the contribution-tree table); plot aggregates have no process to open.
_Avoid_: interactive chart (alone — specify plot–tree linking)

### Tree plot

Node-link plot of the **contribution tree**: process boxes and path-impact ribbons, optically the same as the **Sankey plot**, but drawn from SNEV visits and the Tree tab’s visible table. Plot-type label on the Tree tab is **Tree** (not Flow).
_Avoid_: Flow (rejected plot-type label); Sankey (when meaning this SNEV plot); tree (alone — that is the contribution tree / Tree tab)

### Sankey plot

Node-link plot of an NNEV graph traversal: the same visual grammar as the **tree plot** (boxes, ribbons, triangles). Calculated as new-node-each-visit; the **display set** keeps **one box per process** — the visit with the largest **path impact**, not the first visit Brightway happened to create. A process with a small path to the reference flow and a large path later must follow the large path (Individual path impact hops that visit). Circular supply (A consumes B, B consumes A) still shows two process boxes, not an unfolded A→B→A path. That path unfolding belongs on the **contribution tree**. Shown on the LCA Results **Sankey** tab (no contribution-tree table). The **calculated graph** is the NNEV visits so far (grows only); the drawn boxes are the unique-process display set, which **Adjust policy** can shrink without discarding calculation. Clicking a process grows or shrinks that display set (like expanding a contribution-tree row): if **any NNEV visit of this process** is not yet traversed, calculate **one hop** per unopened visit (Stoppable like **Adjust**; Stop leaves the graph as before that click), then show **every** unique-process supplier of those visits (engine **cutoff** only — not the Adjust path/cumulative filters). Already-shown processes stay one box. If some cutoff suppliers are already calculated but hidden by Adjust, the next click reveals them; a further click collapses exclusive suppliers. Coverage and path targets stay on **Adjust**. Collapsing a process hides unique-process suppliers that are not also **ancestors** in the current display set (circular-supply partners that remain on a path from the reference flow stay drawn); calculation is not discarded. Right-click **Open process** opens **Activity Details** for that unique process (plot aggregates have no process to open).
_Avoid_: calling the Tree-tab node-link plot Sankey; unfolding the same process twice on the Sankey

### Graph explorer

View of the opened process on the **Activity Details** Graph tab (not a standalone AB2-style Graph Explorer tab): one box per process, arrows for technosphere **input flows** and **output flows** (product / amount / unit, no LCA impact). Arrows follow **physical direction** (waste generator → treatment, including negative Brightway amounts); there is no “flip negative flows” control. Labels show the **physical quantity** (absolute amount). Arrow thickness does not encode amount (amounts are not commensurate across products); product, amount, and unit are on the label. Once two processes are both shown, **Show only direct up-/downstream flows** (on by default) draws only the flows that were expanded; uncheck it to draw **every** technosphere flow among the visible processes. The first Graph-tab open shows **that process and the counterpart processes listed on its inputs and outputs (capped at 10 per side, largest |amount| first)** — suppliers of inputs and destinations of listed waste/product output exchanges — plus the **functional flows** of the opened process as red, thicker arrows to a dashed **N consumers** / **N suppliers** box until those counterparts are expanded (click the flow, the box, or the matching triangle). It does **not** add reverse-lookup **consumers** of the functional product until that expand. **Remainder** (`N more processes`) is leftover listed inputs/outputs only, not consumers. Neighbours do not get incoming stubs — leftover listed hops stay on remainder boxes; the only stubs drawn are the opened process's functional-flow arrows (until the dashed **N consumers** / **N suppliers** box covers them). Each side has separate **expand** and **collapse** controls. **Collapse** on a side hides the counterpart boxes that were expanded from **that** process on that side, plus anything that exists in the explorer only through them — not “undo the last 10.” Right-click **Open process** opens Activity Details (same command as the **tree plot** / **Sankey plot**); left-click on the box does not open or expand. **Alt+click** (or **Delete** when that process is selected) **removes** that process from the explorer; the opened process cannot be removed. Removing a process also drops counterparts that exist in the explorer **only through it** (same exclusive rule as collapse). **Biosphere / elementary flows** are not shown. Listed **substitution** exchanges (Flows tab outputs, or negative substitution on inputs) are green arrows from the **substituting process** to the **avoided process** (hover: Substitution); the amount is the substitution amount, distinct from a zero coproduct of the substituting process. Dropping a process onto the explorer adds a technosphere flow when the database is writable (same command as **Flows**). A **hop** is one expand along a clicked flow, or one expand upstream or downstream from a single process. A hop is not a contribution-tree **tier**. Each expand adds at most **10** new process boxes, **largest |amount| first**. Leftover counterparts are a **remainder** control (`N processes have not been expanded`), not process boxes and not a silent sample. Clicking the remainder **expands 10 more** (the last page may be fewer). Distinct from the **Sankey plot** (box click grows the unique-process display set) and the **contribution tree**.
_Avoid_: neighbourhood; calling this view hops; calling a Graph explorer hop a tier; activity graph (legacy); calling this Sankey or a contribution tree; Graph tab (the chrome, not the view); treating a Graph explorer process-box click like Sankey; opening a process from a left-click on the Graph explorer box; treating the remainder as a process; Expand all of a large remainder; collapse as undo-last-10; biosphere on the Graph explorer; Shift+click on a process box to expand downstream; Flip negative flows (AB2 checkbox); Graph explorer arrow width as |amount|; a standalone Graph Explorer tab (AB2); incoming stubs on neighbour process boxes

### Color by

Plot-only recoding of node or segment **fill**. **Direct impact** (default): sequential log-intensity fill of |direct % of total| — blue if > 0, green if < 0, white if 0 (same hues as the Tree table’s Direct impact column). **Product**, **Process**, **Location**, **Database**: categorical. On the tree/Sankey plots, ribbons stay red/green by **path impact** sign; **Color by** recodes boxes only. Distinct from **plot aggregation** (which merges siblings).
_Avoid_: aggregate by (when meaning tint)

### Plot aggregation

Plot-only rollup of **sibling** nodes under the same parent by a metadata field (Product, Process, Location, Unit, Database). Band or ribbon width and direct-impact fill use summed impacts; the tree table is unchanged. On the **tree plot** and **Sankey plot**, an aggregate is a **leaf**: upstream of the merged visits is not drawn; click toggles the parent, not a synthetic node.
_Avoid_: aggregate the contribution tree (alone — plot aggregation is plot-only)

### Flow amount

The scaled technosphere demand for a contribution-tree node (`node.supply_amount`), expressed in the reference product's unit. Shown in the "Flow amount" and "Unit" columns of the contribution tree table, and on tree/Sankey **flow** hovers.
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
| “activity graph” / Graph tab (the view) / neighbourhood | Graph explorer                                                                           |
| “parameterized exchanges” (the concept or Parameters page section) | parameterized flows                                                                      |
