# D3 7.9 with dagre-d3-es for WebEngine graphs

Sankey, graph explorer, the activity graph, spinner, and Tree D3 plots share one vendored D3. Stock dagre-d3 is unmaintained on D3 v4, so the app vendors **D3 7.9.0** and a pinned **dagre-d3-es 7.0.14** IIFE (D3 from the page global) instead of keeping a second D3 major or staying on v4.

## Status

accepted

## Considered Options

- Stay on D3 4.13 + dagre-d3 5.14 (no upgrade).
- Two D3 files (v4 for dagre pages, v7 for Tree plots).
- D3 7.9 everywhere + dagre-d3-es 7.0.14 (chosen).

## Consequences

- App JS must use D3 6+ listener signatures (`event` first) and must not read `d3.event`.
- Layout still uses the existing dagre/graphlib script; only the D3 renderer is dagre-d3-es.
- Graph explorer is in the blast radius: it must keep working, but its interaction is not redesigned here.
