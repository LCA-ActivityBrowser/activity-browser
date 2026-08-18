# Sankey calculated graph continues like the contribution tree

The Sankey plot used to start a new NNEV walk from the functional unit whenever **Adjust policy** changed, and treated an untraversed process as terminal. We keep one **calculated graph** per reference flow / impact category / scenario / cutoff and continue it (Adjust planners and one-hop clicks); the unique-process **display set** can shrink without discarding calculation. A full heap walk to a visit cap unrolls circular supply and throws away work on the next policy; demand-driven hops match the **contribution tree** without drawing the same process twice.

## Status

accepted

## Considered Options

- Re-run NNEV from the functional unit for every Adjust (rejected: slow; unrolls cycles).
- Share the Tree’s SNEV graph with the Sankey (rejected: path unfolding belongs on the contribution tree).
- Continue one NNEV graph; unique-process display set + one-hop click (chosen).

The unique-process representative is the visit with the largest |path impact|, not the first NNEV visit. A small path to the reference flow must not steal the box or the hop from a later large path. Circular supply still collapses A→B→A to two boxes.
