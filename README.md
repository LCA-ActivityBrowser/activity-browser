[![conda-forge version](https://img.shields.io/conda/vn/conda-forge/activity-browser.svg)](https://anaconda.org/conda-forge/activity-browser)
[![Downloads](https://anaconda.org/conda-forge/activity-browser/badges/downloads.svg)](https://anaconda.org/conda-forge/activity-browser)
![linux](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/linux.png)
![apple](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/apple.png)
![windows](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/windows.png)
[![Pull request tests](https://github.com/LCA-ActivityBrowser/activity-browser/actions/workflows/main.yaml/badge.svg)](https://github.com/LCA-ActivityBrowser/activity-browser/actions/workflows/main.yaml)
[![Coverage Status](https://coveralls.io/repos/github/LCA-ActivityBrowser/activity-browser/badge.svg?branch=main)](https://coveralls.io/github/LCA-ActivityBrowser/activity-browser?branch=main)


# Activity Browser

<img src="https://user-images.githubusercontent.com/33026150/54299977-47a9f680-45bc-11e9-81c6-b99462f84d0b.png" width=100%/>

The **Activity Browser (AB)** is an open-source GUI for Life Cycle Assessment on [Brightway](https://brightway.dev).

### Highlights

- **A productivity tool for Brightway**: model in Brightway (Python) and see the results in the AB or vice versa
- **Fast LCA calculations**: for multiple reference flows, impact categories, and scenarios
- **Advanced modeling:** Use parameters, scenarios (including prospective LCI databases from [premise](https://premise.readthedocs.io/en/latest/)), uncertainties and our Graph Explorer
- **Advanced analyses:** Contribution analyses, Sankey Diagrams, Monte Carlo, and Global Sensitivity Analysis
- **Plugins:** Extend the functionality of Activity Browser with
[Plugins](https://github.com/LCA-ActivityBrowser/activity-browser/wiki/Plugins)


# Installation (AB3)

> [!IMPORTANT]
> **Activity Browser 3**  is moving out of the beta phase anytime soon. It is already far ahead of the AB2 (soon legacy) version.
> It comes with a refreshed UI, runs on Brightway 2.5 and adds multifunctionality via [bw_functional](https://github.com/LCA-ActivityBrowser/bw-functional).
> Please try it and [report issues](https://github.com/LCA-ActivityBrowser/activity-browser/issues/new?template=beta_report.yml).

### Download stand-alone (Windows / macOS / Linux)

**No Python required.** Installers for Windows, macOS (Apple Silicon), and Linux:

<a href="https://github.com/LCA-ActivityBrowser/activity-browser/releases"><img src="https://img.shields.io/badge/Download-stand--alone%20(GitHub%20Releases)-0A66C2?style=for-the-badge&logo=github&logoColor=white" alt="Download stand-alone from GitHub Releases"></a>

See the [Installation Guide](https://lca-activitybrowser.github.io/activity-browser/getting-started/installation.html#stand-alone-installers) for additional instructions.

### Installation via PyPI and Conda 
Please follow the
[Installation Guide](https://lca-activitybrowser.github.io/activity-browser/getting-started/installation.html).

See also: [Activity Browser 3 Documentation](https://lca-activitybrowser.github.io/activity-browser/)

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

# License and Copyright

This project is licensed under the terms of the 
GNU Lesser General Public License (LGPL v3 or later), 
see [license file](https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/LICENSE.txt).

* Copyright (c) 2014-2026: Bernhard Steubing
* Copyright (c) 2014-2016: ETH Zürich
* Copyright (c) 2018-2024: Universiteit Leiden

# AB 2 (legacy version)

Activity Browser 2 is the previous stable version, but not actively maintained anymore (Brightway2). 
Prefer AB3 beta for new work.

[Installation Guide (wiki)](https://github.com/LCA-ActivityBrowser/activity-browser/wiki/Installation-Guide)
```bash
conda create -n ab -c conda-forge activity-browser
conda activate ab
activity-browser
```
