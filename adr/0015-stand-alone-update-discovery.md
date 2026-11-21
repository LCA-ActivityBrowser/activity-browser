# Stand-alone updates discovered by `*-stand-alone` release tags

Stand-alone is promoted manually and can lag PyPI/conda, and the repo’s GitHub **Latest** badge is not “latest stand-alone.” We discover the newest stand-alone by listing GitHub Releases and taking the highest PEP 440 base among tags ending in `-stand-alone`, and we point docs and the in-app updater at the Releases / that release page rather than fixed asset URLs or a rolling `stand-alone` download tag. New builds stamp the public AB version in package metadata and detect the channel via `sys.frozen` (display/tags still use `-stand-alone`).

## Status

accepted

## Considered Options

- Repo Latest / `/releases/latest/download/…` — wrong when Latest is a non–stand-alone release or when PyPI moved but stand-alone was not promoted
- Rolling tag with stable filenames + optional `latest.yml` — good for fixed docs download links; extra moving parts we deferred
- Filter immutable `{AB}-stand-alone` tags via the Releases API — channel-local, history for free, matches open-browser update UX

## Consequences

- Docs buttons link to the Releases page (not direct installer URLs) until a later alias is added
- Update checker must call the GitHub API (or equivalent) and ignore PyPI for the stand-alone install channel
