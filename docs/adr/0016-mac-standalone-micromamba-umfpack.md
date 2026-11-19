# Mac stand-alone freezes via micromamba for scikit-umfpack

Stand-alone macOS Apple Silicon needs Brightway’s fast sparse solver (`scikit-umfpack` + SuiteSparse). That stack is reliable as conda-forge binaries but only an sdist on PyPI, so the Mac Build Executable leg uses a **micromamba** freeze env while Windows/Linux stay on **`uv` + pypardiso**. CI fails if umfpack cannot be imported or bundled into the `.app`.

## Status

accepted

## Considered Options

- Keep `uv` on Mac and `pip install scikit-umfpack` from source (Homebrew SuiteSparse) — fragile compile on CI
- Hybrid: `uv` prefix plus side-loaded conda dylibs — brittle rpaths / two prefixes
- Micromamba freeze env on Mac only, collect umfpack into the `.app` — one coherent prefix, matches what already works for conda users

## Consequences

- Build Executable has divergent Mac vs Win/Linux dependency sync steps
- PyPI installs still need an optional post-install (documented); no hard `scikit-umfpack` marker dep
- Conda recipe unchanged for this decision
