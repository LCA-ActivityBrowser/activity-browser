---
title: Home
layout: home
nav_order: 1
description: "The Activity Browser documentation aims to help users get started and to document all features in Activity Browser."
permalink: /
---
# Activity Browser documentation
{: .fs-9 }

Learn how to use the Activity Browser, find tutorials, and get detailed information about its features.
{: .fs-6 .fw-300 }

[Install now](getting-started/installation){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[Visit our GitHub](https://github.com/LCA-ActivityBrowser/activity-browser){: .btn .fs-5 .mb-4 .mb-md-0 .mr-2 }
[Report a bug or feature request](https://github.com/LCA-ActivityBrowser/activity-browser/issues/new?template=ab3_report.yml){: .btn .fs-5 .mb-4 .mb-md-0 }

## New in Activity Browser 3

Activity Browser 3 is the current version and the one we recommend for new work. It runs on Brightway 2.5, adds [multifunctionality](advanced-topics/multifunctional-databases/) via [bw_functional](https://github.com/LCA-ActivityBrowser/bw-functional), and includes a refreshed interface.

Activity Browser 2 remains available as a legacy install from conda-forge, but it is not actively maintained. Prefer AB3 for new projects.

{: .warning }
> Back up critical projects before opening them in a new major version. AB3 uses the Brightway 2.5 stack; AB2 plugins are not carried forward. If you open an older Brightway project, see [Brightway Legacy projects](advanced-topics/brightway-legacy).

## What you can do

- Run fast LCA calculations for multiple reference flows, impact categories, and scenarios
- Use parameters, scenarios (including prospective LCI databases from [premise](https://premise.readthedocs.io/en/latest/)), uncertainties, and the Graph Explorer
- Explore results with contribution analyses, Sankey diagrams, Monte Carlo, and global sensitivity analysis
- Work with Brightway in Python and see the same project data in the Activity Browser (and the other way around)

Start with [Getting started](getting-started/) after you [install](getting-started/installation).

## Reporting issues

Bugs and feature requests belong as [GitHub issues](https://github.com/LCA-ActivityBrowser/activity-browser/issues/new?template=ab3_report.yml). Include the version (About / `pip show`), install channel (pip, conda, or stand-alone), and OS when reporting a bug.

{: .important }
> Creating this site is an ongoing project. While we aim to have it as complete as possible, sections may be missing or incomplete. If you want to contribute, see our [contributing guidelines](https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/CONTRIBUTING.md).
