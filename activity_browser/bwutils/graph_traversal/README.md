# graph_traversal

Brightway/graph helpers for the LCA Results **Tree** tab and **Sankey** tab. No Qt.

## Placement

- Brightway-only graph math → this package (`bwutils/graph_traversal/`)
- Application-aware Tree and Sankey pages → `activity_browser/app/pages/lca_results/`
- Do not put display-set, Adjust, unique-process, or payload math in the Sankey tab widget

See ADR-0001 (layering) and ADR-0008 (this package).

## Modules

Import from the four modules explicitly. The package `__init__` does not re-export symbols.

| Module | Role |
|---|---|
| **`engine`** | Visit-based: parent/child map, percents, tiers, coverage, Adjust / display set, traverse-from-node, open-process refs, node-link payload for the Tree plot (and as the base Sankey payload). No unique-process flag. Must not import `tree`, `sankey`, or `partition_plots`. |
| **`tree`** | Contribution-tree table flatten, SNEV footer stats, table direct-impact intensity. May import `engine`. Must not import `sankey`. |
| **`sankey`** | One box per process (highest \|path impact\| visit), unique-process stats, click hops, inventory-direct overlay, mapped edge amounts. Wraps engine Adjust / display set / payload. May import `engine`. Must not import `tree` or `partition_plots`. |
| **`partition_plots`** | Horizontal/vertical chain, sunburst, treemap/icicle, partition JSON payload, plot click target. May import `engine`. Must not import `sankey`. |

`PLOT_AGGREGATE_FIELDS` / `PLOT_AGGREGATE_LABELS` live on **engine** so both tabs and the node-link payload share them without Sankey importing partition plots.

## Glossary

Use terms from root `CONTEXT.md`: contribution tree, Tree plot, Sankey plot, adjust policy, display set, unique process, calculated graph.
