[![conda-forge version](https://img.shields.io/conda/vn/conda-forge/activity-browser.svg)](https://anaconda.org/conda-forge/activity-browser)
[![Downloads](https://anaconda.org/conda-forge/activity-browser/badges/downloads.svg)](https://anaconda.org/conda-forge/activity-browser)
![linux](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/linux.png)
![apple](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/apple.png)
![windows](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/windows.png)
[![Pull request tests](https://github.com/LCA-ActivityBrowser/activity-browser/actions/workflows/main.yaml/badge.svg)](https://github.com/LCA-ActivityBrowser/activity-browser/actions/workflows/main.yaml)
[![Coverage Status](https://coveralls.io/repos/github/LCA-ActivityBrowser/activity-browser/badge.svg?branch=main)](https://coveralls.io/github/LCA-ActivityBrowser/activity-browser?branch=main)


# Activity Browser

<img src="https://user-images.githubusercontent.com/33026150/54299977-47a9f680-45bc-11e9-81c6-b99462f84d0b.png" width=100%/>

The **Activity Browser (AB) is an open source software for Life Cycle Assessment (LCA)** that builds on [Brightway2](https://brightway.dev).

### Some highlights

- **Fast LCA calculations**: for multiple reference flows, impact categories, and scenarios
- **A productivity tool for brightway**: model in brightway (python) and see the results in the AB or vice-versa
- **Advanced modeling:** Use parameters, scenarios (including prospective LCI databases from [premise](https://premise.readthedocs.io/en/latest/)), uncertainties and our Graph Explorer
- **Advanced analyses:** Contribution analyses, Sankey Diagrams, Monte Carlo, and Global Sensitivity Analysis
- **Plugins:** Extend the functionality of Activity Browser with 
[Plugins](https://github.com/LCA-ActivityBrowser/activity-browser/wiki/Plugins)

# Contents
- [Installation](#installation)
- [First Steps](#first-steps)
- [Contributing](#contributing)
- [Developers](#developers)
- [Copyright](#copyright)
- [License](#license)

# Installation

## Step-by-step guide
See our 
[Installation Guide](https://github.com/LCA-ActivityBrowser/activity-browser/wiki/Installation-Guide) 
wiki page for a step-by-step guide to installing Activity Browser.

## The quick way
Or you can install and start the activity-browser like this:

```bash
conda create -n ab -c conda-forge activity-browser
conda activate ab
activity-browser
```

# First Steps
See our
[Getting Started](https://github.com/LCA-ActivityBrowser/activity-browser/wiki/Getting-Started)
wiki page to learn how to get started using Activity Browser.

# Contributing

**The Activity Browser is a community project. Your contribution counts!**

If you have ideas for improvements to the code or documentation or want to propose new features, please take a look at our [contributing guidelines](CONTRIBUTING.md) and open issues and/or pull-requests.

If you experience problems or are suffering from a specific bug, please [raise an issue](https://github.com/LCA-ActivityBrowser/activity-browser/issues) here on github.

# Developers

### Current main developers

- Bernhard Steubing (b.steubing@cml.leidenuniv.nl) (creator)
- Marin Visscher (m.r.visscher@cml.leidenuniv.nl) (main developer)
- Marc van der Meide (m.t.van.der.meide@cml.leidenuniv.nl) (maintainer)

### Important contributors

- [Adrian Haas](https://github.com/haasad)
- [Chris Mutel](https://github.com/cmutel)
- [Daniel de Koning](https://github.com/dgdekoning)
- [Jonathan Kidner](https://github.com/Zoophobus)
- [Remy le Calloch](https://remy.lecalloch.net)

# Copyright
- 2016-2023: Bernhard Steubing (Leiden University)

# License
You can find the license information for Activity Browser in the [license file](https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/LICENSE.txt).
