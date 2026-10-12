# Pandas 3 first, compatible with pandas 2.3+

Activity Browser targets pandas 3 semantics (`str` for scalar text, Copy-on-Write, `pd.isna` / `is_string_dtype`) while remaining installable on pandas 2.3.x. Constraint is `pandas>=2.3,<4`. On 2.3 only, startup (and tests) set `mode.copy_on_write = True` and `future.infer_string = True` so 2.3 matches 3; those options are not set on pandas 3. Tuples, lists, and dicts stay in explicit `object` columns (MDS `key` / `categories` / `synonyms` / `properties`, scenario `from key` / `to key`); they are not stringified, flattened, or stored as Arrow structs. Scalar text uses `"str"`. The MetaDataStore pickle cache downcasts `"str"` to `object` on flush and carries a pandas-major stamp so a major switch rebuilds silently.

## Status

accepted

## Considered Options

- Pandas 3 only (`>=3,<4`) — simpler, breaks current 2.x conda/pip envs.
- Floor at 2.2.1 without forcing CoW / `infer_string` — two runtime models; 2.x CI would not catch 3.x bugs.
- Keep all MDS text as `object` — cheaper dual support, fights pandas 3.
- Flatten or stringify identity tuples — schema change, fights Brightway keys.

## Consequences

- Write CoW-safe assignment (`loc` / column replace). Do not use `dtype == object` to mean “text.”
- IO must `astype(object)` before putting tuples into columns that pandas inferred as `"str"`.
- If Brightway is not pandas-3-clean, keep the upper pin at `<3` until it is; AB code stays pandas-3-first.
- CI: default resolver (pandas 3) plus one Ubuntu / Python 3.12 job on latest 2.3.x. No pyarrow extra; no DataFrame compatibility wrapper.
- Replaces an earlier draft of this ADR (2.2 floor, MDS text frozen as `object`).
