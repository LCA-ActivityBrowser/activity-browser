# Pandas 2.x and 3.x dual support (`>=2.2.1,<4`)

Activity Browser supports pandas 2.x and 3.x with constraint `pandas>=2.2.1,<4`. The MetaDataStore keeps its hybrid `object`/pickle cache (no string-dtype redesign); a sidecar stamp of the pandas major invalidates the cache across majors. CI keeps the default matrix on the resolver (typically pandas 3) plus one Ubuntu/Python 3.12 job forced to latest pandas 2.x so dual support does not rot.

## Status

accepted

## Considered Options

- Require pandas 3 only — cleaner long-term, breaks existing 2.x envs.
- Open upper bound (`>=2.2.1`) — next major could land unannounced.
- Redesign MetaDataStore schema/cache for native string dtype in the same change — larger than unpinning.

## Consequences

- Hotspot call sites must treat text columns as object **or** string dtype.
- MetaDataStore field schema uses `object` for text columns (not builtin `str`, which becomes StringDtype under pandas 3).
- Scenario SDF key/category parsers must coerce to `object` before storing tuples (string dtype rejects non-strings).
- Tree models: prefer ``get()``/``iat`` for cells; full-row access must use ``iloc[[i]]`` (take), not ``iloc[i]`` (``fast_xs``), under pandas 3.
- Pre-stamp caches rebuild once (missing stamp is a mismatch).
- Replacing pickle / adopting string dtype in the Metadata store remains a follow-up.
