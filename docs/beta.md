---
title: Activity Browser 3
nav_order: 2
---
# Activity Browser 3
{: .fs-9 }

Brightway 2.5, multifunctionality, and a refreshed UI.
{: .fs-6 .fw-300 }

[Report a bug or feature request](https://github.com/LCA-ActivityBrowser/activity-browser/issues/new?template=ab3_report.yml){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }

Activity Browser 3 is the current product line. It runs on Brightway 2.5 and adds multifunctionality and a refreshed interface. Prefer AB3 for new work; Activity Browser 2 remains available as a legacy install from conda-forge.

{: .warning }
> Back up critical projects before opening them in a new major version. AB3 uses the Brightway 2.5 stack; AB2 plugins are not carried forward.

## Installation

See the [installation guide](getting-started/installation.md) for stand-alone, PyPI, and conda options.

#### Quick-Install PyPI
```
pip install activity-browser
```

#### Quick-Install Anaconda
```
conda create -n ab -c conda-forge -c lca -c cmutel lca::activity-browser
conda activate ab
activity-browser
```

Pin `lca::activity-browser`. An unpinned install with `-c conda-forge` first resolves to Activity Browser 2 from conda-forge. Keep `-c cmutel` for the Brightway / Qt stack used by AB3.

## Reporting issues

Bugs and feature requests belong as [GitHub issues](https://github.com/LCA-ActivityBrowser/activity-browser/issues/new?template=ab3_report.yml). Include the version (About / `pip show`), install channel (pip, conda, or stand-alone), and OS when reporting a bug.

Release channels and branching are recorded in [ADR-0017](https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/docs/adr/0017-ab3-release-channels-and-branches.md).
