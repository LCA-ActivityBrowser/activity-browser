# Graph explorer is not graph_traversal

The Activity Details **Graph explorer** walks technosphere flows of the opened process. It does not use `graph_traversal` (SNEV/NNEV visits, path impact, Adjust, unique-process display set). Explorer state and payload live in `bwutils/graph_explorer/`; the Graph tab is a widget; D3 draws boxes and arrows. Mixing this into graph_traversal would fight ADR-0008 and the glossary.

## Status

accepted
