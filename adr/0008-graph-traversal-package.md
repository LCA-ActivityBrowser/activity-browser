# Graph math lives in graph_traversal, not in the navigator tabs

Tree and Sankey share visit-based Adjust, display-set, and node-link payload helpers; unique-process (one box per process) is a Sankey concern. Those helpers live in `bwutils/graph_traversal/` so the Qt pages stay widgets. The engine has no `unique_activities` flag — Sankey wraps the engine, then collapses to the highest-|path impact| visit per process.

## Status

accepted

## Considered Options

- Keep one Tree-named helper module for both tabs (rejected: name fights the glossary; unique-process looks like a contribution-tree flag).
- Put graph math on the Sankey navigator tab (rejected: ADR-0001; widgets must not own traversal).
- Four modules under `graph_traversal`: engine, tree, sankey, partition_plots (chosen).
