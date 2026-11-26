# AB3 release channels and branches

AB3 publishes normal semver only from annotated tags (GitHub Release + PyPI + `lca`); merges to stable do not publish. Branches are `main` (stable), `dev` (integration), and `AB2_legacy` (AB2 critical fixes only); install channels are pip, conda (`lca::activity-browser` for AB3), and stand-alone (`{version}-stand-alone`, ADR-0015). conda-forge stays AB2 until forge-only deps (e.g. `bw_functional`) allow an AB3 feedstock.

## Status

accepted

## Considered Options

- Keep push-to-`beta` timestamp `3.0.0b…` publishes as the public cadence — simple, but never a normal semver product
- Put AB3 on conda-forge at first stable — blocked while recipe deps are not forge-only
- Encode release process in `CONTEXT.md` — rejected; glossary stays install-channel vocabulary only

## Consequences

- Contributor flow is `feature → dev → main` (merge commits into `main`); public versions only from tags
- Docs must pin `lca::activity-browser` and warn that unpinned conda-forge still resolves AB2
- `AB2_legacy` may receive critical fix tags; no AB2 feature development
- First complete stable cut (`3.0.0`) includes pip, `lca`, and stand-alone; later tags may omit stand-alone when package-only
- Release notes: GitHub native auto-generated notes (`.github/release.yml` PR labels) on the GitHub Release, plus curated preamble via Edit release after the tag
