# Pedigree is a stored recipe on flows, applied opt-in

Ecoinvent and Brightway store pedigree scores on a flow separately from the sampled uncertainty; Monte Carlo only samples the latter. Activity Browser treats pedigree as a stored recipe (five scores plus basic uncertainty) for lognormal spread.

The uncertainty dialog hides the pedigree editor until **Use pedigree** is checked. Checking applies: lognormal spread from the recipe, persisted on OK. Unchecking restores the sampled fields from just before the check and leaves the stored recipe. Changing or removing the sampled uncertainty while using pedigree keeps that new choice, turns use pedigree off, and leaves the recipe. Clearing pedigree restores the sampled fields and deletes the stored recipe on OK; checking use pedigree again before OK undoes Clear.

Pedigree is not offered on parameter objects or characterization factors. Parameterized flows still get pedigree because they are flows, not parameters. Pedigree is not restored as a wizard or a separate table column.
