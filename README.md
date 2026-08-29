[![PyPI version](https://img.shields.io/pypi/v/activity-browser.svg)](https://pypi.org/project/activity-browser/)
[![PyPI downloads](https://static.pepy.tech/badge/activity-browser)](https://pepy.tech/projects/activity-browser)
[![PyPI downloads](https://img.shields.io/pypi/dm/activity-browser.svg)](https://pypi.org/project/activity-browser/)
![linux](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/linux.png)
![apple](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/apple.png)
![windows](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/windows.png)
[![Pull request tests](https://github.com/LCA-ActivityBrowser/activity-browser/actions/workflows/testing.yaml/badge.svg)](https://github.com/LCA-ActivityBrowser/activity-browser/actions/workflows/testing.yaml)
[![Docs](https://img.shields.io/badge/docs-AB3-blue)](https://lca-activitybrowser.github.io/activity-browser/)
[![License](https://img.shields.io/badge/license-LGPL%20v3+-blue.svg)](https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/LICENSE.txt)

<!--
Other badges
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://pypi.org/project/activity-browser/)
[![Brightway](https://img.shields.io/badge/Brightway-2.5-green)](https://brightway.dev)
[![conda lca version](https://img.shields.io/conda/vn/lca/activity-browser.svg)](https://anaconda.org/lca/activity-browser)
[![conda lca downloads](https://img.shields.io/conda/dn/lca/activity-browser.svg?label=conda%20lca%20downloads)](https://anaconda.org/lca/activity-browser)
[![Stand-alone](https://img.shields.io/badge/download-stand--alone-0A66C2?logo=github)](https://github.com/LCA-ActivityBrowser/activity-browser/releases)
[![Coverage Status](https://coveralls.io/repos/github/LCA-ActivityBrowser/activity-browser/badge.svg?branch=main)](https://coveralls.io/github/LCA-ActivityBrowser/activity-browser?branch=main)
[![Stand-alone downloads](https://img.shields.io/github/downloads/LCA-ActivityBrowser/activity-browser/total.svg?label=stand-alone%20downloads)](https://github.com/LCA-ActivityBrowser/activity-browser/releases)
[![conda lca downloads](https://img.shields.io/conda/dn/lca/activity-browser.svg?label=conda%20lca%20downloads)](https://anaconda.org/lca/activity-browser)
[![Traffic report](https://img.shields.io/badge/traffic-github--repo--stats-lightgrey)](https://github.com/LCA-ActivityBrowser/activity-browser/blob/github-repo-stats/LCA-ActivityBrowser/activity-browser/latest-report/report.html)
-->

# Activity Browser

<img src="https://user-images.githubusercontent.com/33026150/54299977-47a9f680-45bc-11e9-81c6-b99462f84d0b.png" width=100%/>

The **Activity Browser (AB)** is an open-source GUI for Life Cycle Assessment on [Brightway](https://brightway.dev).

### Highlights

- **A productivity tool for Brightway**: model in Brightway (Python) and see the results in the AB or vice versa
- **Fast LCA calculations**: for multiple reference flows, impact categories, and scenarios
- **Advanced modeling:** Use parameters, scenarios (including prospective LCI databases from [premise](https://premise.readthedocs.io/en/latest/)), uncertainties and our Graph Explorer
- **Advanced analyses:** Contribution analyses, Sankey Diagrams, Monte Carlo, and Global Sensitivity Analysis
- **Plugins:** Extend Activity Browser with [Plugins](https://lca-activitybrowser.github.io/activity-browser/plugins/)

> [!NOTE]
> **Activity Browser 3** is the version we recommend for new installs. 
> It is far ahead of the [AB2](#ab-2-legacy-version) (legacy) version.
> It comes with a refreshed UI, runs on Brightway 2.5, and adds multifunctionality via [bw_functional](https://github.com/LCA-ActivityBrowser/bw-functional).
>
> [Learn more](https://lca-activitybrowser.github.io/activity-browser/#new-in-activity-browser-3) about AB3.

# Installation

## Stand-alone installers

**No Python required.** Installers for Windows, macOS (Apple Silicon), and Linux:

<a href="https://github.com/LCA-ActivityBrowser/activity-browser/releases"><img src="https://img.shields.io/badge/Download-stand--alone%20(GitHub%20Releases)-0A66C2?style=for-the-badge&logo=github&logoColor=white" alt="Download stand-alone from GitHub Releases"></a>

[![Stand-alone downloads](https://img.shields.io/github/downloads/LCA-ActivityBrowser/activity-browser/total.svg?label=stand-alone%20downloads)](https://github.com/LCA-ActivityBrowser/activity-browser/releases)

> [!Note]
> Choose a release tag ending in `-stand-alone` and download the installer for your OS.
>
> Windows/macOS builds are unsigned; browsers or Gatekeeper/SmartScreen may warn on first download/launch.
See the [Installation Guide](https://lca-activitybrowser.github.io/activity-browser/getting-started/installation.html#stand-alone-installers) for additional instructions.

## Installation via PyPI and Conda

Please follow the [Installation Guide](https://lca-activitybrowser.github.io/activity-browser/getting-started/installation.html).

## AB 2 (legacy version)
[![conda-forge version](https://img.shields.io/conda/vn/conda-forge/activity-browser.svg)](https://anaconda.org/conda-forge/activity-browser)
[![Downloads](https://anaconda.org/conda-forge/activity-browser/badges/downloads.svg)](https://anaconda.org/conda-forge/activity-browser)
![linux](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/linux.png)
![apple](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/apple.png)
![windows](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/windows.png)
<!--
[![Pull request tests](https://github.com/LCA-ActivityBrowser/activity-browser/actions/workflows/testing.yaml/badge.svg)](https://github.com/LCA-ActivityBrowser/activity-browser/actions/workflows/testing.yaml)
[![Coverage Status](https://coveralls.io/repos/github/LCA-ActivityBrowser/activity-browser/badge.svg?branch=main)](https://coveralls.io/github/LCA-ActivityBrowser/activity-browser?branch=main)
-->

> [!Warning]
> Activity Browser 2 is the previous stable version, but not actively maintained anymore (Brightway2).
> Prefer AB3 for new work.

```bash
conda create -n ab -c conda-forge activity-browser
conda activate ab
activity-browser
```

# First Steps
See our
[Getting Started](https://lca-activitybrowser.github.io/activity-browser/getting-started/) page to learn how to get started with the Activity Browser.



# Contributing

**The Activity Browser is a community project. Your contribution counts!**

If you have ideas for improvements to the code or documentation or want to propose new features, please take a look at our [contributing guidelines](CONTRIBUTING.md) and open issues and/or pull-requests.

If you experience problems or are suffering from a specific bug, please [raise an issue](https://github.com/LCA-ActivityBrowser/activity-browser/issues) here on github.

# Developers

### Current maintainers

- [Bernhard Steubing](https://github.com/bsteubing) (creator, maintainer)
- [Marc van der Meide](https://github.com/marc-vdm) (maintainer)

### Important contributors

- [Marin Visscher](https://github.com/mrvisscher)
- [Jonathan Kidner](https://github.com/Zoophobus)
- [Remy le Calloch](https://remy.lecalloch.net)
- [Daniel de Koning](https://github.com/dgdekoning)
- [Adrian Haas](https://github.com/haasad)
- [Chris Mutel](https://github.com/cmutel)

# License

Activity Browser is free software licensed under the
GNU Lesser General Public License, version 3 or later (LGPL-3.0-or-later).
See [LICENSE.txt](LICENSE.txt).

Copyright (c) Activity Browser Developers.
The copyright holders and the years covered by each notice are listed in
[COPYRIGHT.txt](COPYRIGHT.txt).


