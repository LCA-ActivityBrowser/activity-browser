[![conda-forge version](https://img.shields.io/conda/vn/conda-forge/activity-browser.svg)](https://anaconda.org/conda-forge/activity-browser)
[![Downloads](https://anaconda.org/conda-forge/activity-browser/badges/downloads.svg)](https://anaconda.org/conda-forge/activity-browser)
![linux](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/linux.png)
![apple](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/apple.png)
![windows](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/windows.png)
[![Pull request tests](https://github.com/LCA-ActivityBrowser/activity-browser/actions/workflows/main.yaml/badge.svg)](https://github.com/LCA-ActivityBrowser/activity-browser/actions/workflows/main.yaml)
[![Coverage Status](https://coveralls.io/repos/github/LCA-ActivityBrowser/activity-browser/badge.svg?branch=master)](https://coveralls.io/github/LCA-ActivityBrowser/activity-browser?branch=master)


# Activity Browser

<img src="https://user-images.githubusercontent.com/33026150/54299977-47a9f680-45bc-11e9-81c6-b99462f84d0b.png" width=100%/>

The **Activity Browser (AB) is an open source software for Life Cycle Assessment (LCA)** that builds on [Brightway2](https://brightway.dev).

[Video tutorials](https://www.youtube.com/channel/UCsyySKrzEMsRFsWW1Oz-6aA/) are available on youtube.

Please also read and cite our [scientific paper](https://doi.org/10.1016/j.simpa.2019.100012).


### Some highlights

- **Fast LCA calculations**: for multiple reference flows, impact categories, and scenarios
- **A productivity tool for brightway**: model in brightway (python) and see the results in the AB or vice-versa 
- **Advanced modeling:** Use parameters, scenarios (including prospective LCI databases from [premise](https://premise.readthedocs.io/en/latest/)), uncertainties and our Graph Explorer
- **Advanced analyses:** Contribution analyses, Sankey Diagrams, Monte Carlo, and Global Sensitivity Analysis

# Contents
- [Installation](#installation)
    - [The quick way](#the-quick-way)
    - [The thorough way](#the-thorough-way)
        - [Conda](#conda)
        - [Install the AB with ecoinvent >=3.9](#install-the-ab-with-ecoinvent-39)
        - [Install the AB with ecoinvent <3.9](#install-the-ab-with-older-ecoinvent-versions-39)
- [Updating the AB](#updating-the-ab)
- [Getting started](#getting-started)
    - [Running the AB](#running-the-ab)
    - [Importing LCI databases](#importing-lci-databases)
    - [Additional Resources](#additional-resources)
- [Contributing](#contributing)
- [Developers](#developers)
- [Copyright](#copyright)
- [License](#license)

# Installation

## The quick way

You can install and start the activity-browser like this:

```bash
conda create -n ab -c conda-forge activity-browser
conda activate ab
activity-browser
```

## The thorough way

| :warning: The activity browser has dropped support for python versions below `3.8`|
|---|
| You should re-install if you have an older installation of the activity browser which doesn't use `python >= 3.8` (you can check with `conda list` or `python --version` in your conda environment). You can remove your existing environment with `conda remove -n ab --all` or choose a new environment name (instead of `ab`). Re-installing will not affect your activity-browser/brightway projects. |

### Conda

We recommend that you use **conda** to manage your python installation. You can install [Anaconda](https://www.anaconda.com/products/individual) or the more compact [miniconda](https://conda.io/miniconda.html) (Python 3 of course) for your operating system. Installation instructions for miniconda can be found [here](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html). See also the [conda user guide](https://docs.conda.io/projects/conda/en/latest/user-guide/index.html) or the [Conda cheat sheet](https://docs.conda.io/projects/conda/en/latest/_downloads/843d9e0198f2a193a3484886fa28163c/conda-cheatsheet.pdf).

Skip this step if you already have a working installation of anaconda or miniconda, but make sure to keep your conda installation up-to-date: `conda update conda`.

### Add the Conda-Forge channel
The activity-browser has many dependencies that are managed by the [conda-forge](https://conda.io/docs/user-guide/tasks/manage-channels.html) channel. Open a cmd-window or terminal (in Windows you may have to use the Anaconda prompt) and type the following:

```bash
conda config --prepend channels conda-forge
```
### Install the AB with ecoinvent >=3.9
After prepending the Conda-Forge channel the following line should be executed within the command prompt/terminal to install the AB and it's dependencies.

```bash
conda create -n ab activity-browser
```
This will install the Activity Browser with the latest version of the Brightway2 libraries (currently excluding Brightway2.5 libraries).

### Install the AB with older ecoinvent versions (<3.9)

If you want to work with with older versions of ecoinvent (<3.9) in the AB, a different Biosphere3 database needs to be installed. This requires a _**different version of the bw2io library**_ to be installed, see also [here](https://github.com/brightway-lca/brightway2-io). Note that this version of bw2io can ONLY work with ecoinvent versions < 3.9. If you want to work with version > 3.9 AND < 3.9, the only solution currently available is to use two separate virtual environments (i.e. two AB installations).

To install a version of the AB that can handle ecoinvent versions <3.9, do the following: For a new installation from the conda-forge repository the same initial steps need to be made: Prepending the Conda-Forge repository in the channels, and installing the AB and dependencies. After the successful installation, the following two commands need to be executed before running the AB: <i>1)</i> Remove the latest version of the Brightway2 Input-Output library, <i>2)</i> Install an older version of the Brightway2 Input-Output library.

```bash
conda remove --force bw2io
conda install bw2io=0.8.7
```

#### Activity Browser is installed

At this point the activity-browser and all of its dependencies will be installed in a new conda environment called `ab`. You can change the environment name `ab` to whatever suits you.

# Updating the AB

We recommend to regularly update the AB to receive new features & bugfixes. These commands will update the activity-browser and all of its dependencies in the conda environment called `ab`.

```bash
conda activate ab
conda update activity-browser
```

# Getting started

## Running the AB

First activate the environment where the activity browser is installed:

```bash
conda activate ab
```

Then simply run `activity-browser` and the application will open.

## Importing LCI databases

- In the `Project`-tab there is initially a button called _"Add default data (biosphere flows and impact categories)"_. Click this button to add the default data. This is equivalent to `brightway2.bw2setup()` in python.
- After adding the default data, you can import a database with the _"Import Database"_-Button. Follow the instructions of the database import wizard. Imports can be done in several ways:
    - Directly from the ecoinvent homepage (ecoinvent login credentials required)
    - From a 7zip archive
    - From a directory with ecospold2 files (same as in brightway2)
    - From Excel files using the brightway Excel format

## Additional Resources

- [Youtube tutorials](https://www.youtube.com/channel/UCsyySKrzEMsRFsWW1Oz-6aA/)
- [AB Wiki](https://github.com/LCA-ActivityBrowser/activity-browser/wiki)
- [AB scientific article](https://doi.org/10.1016/j.simpa.2019.100012)
- [Brightway2](https://brightway.dev/)
- [Global Sensitiviy Analysis paper](https://onlinelibrary.wiley.com/doi/10.1111/jiec.13194) describing GSA as implemented in the AB; see also our [wiki](https://github.com/LCA-ActivityBrowser/activity-browser/wiki/Global-Sensitivity-Analysis)
- [Modular LCA paper](https://link.springer.com/article/10.1007/s11367-015-1015-3); [documentation modular LCA](http://activity-browser.readthedocs.io/en/latest/index.html); re-implementation of modular LCA into the AB is [ongoing](https://github.com/marc-vdm/activity-browser/tree/mLCA)

# Contributing

**The Activity Browser is a community project. Your contribution counts!**

If you have ideas for improvements to the code or documentation or want to propose new features, please take a look at our [contributing guidelines](CONTRIBUTING.md) and open issues and/or pull-requests.

If you experience problems or are suffering from a specific bug, please [raise an issue](https://github.com/LCA-ActivityBrowser/activity-browser/issues) here on github.

# Developers

### Current main developers

- Bernhard Steubing (b.steubing@cml.leidenuniv.nl) (creator)
- Jonathan Kidner (j.h.kidner@cml.leidenuniv.nl) (lead developer)

### Important contributers

- Adrian Haas (haasad@ethz.ch)
- Chris Mutel (cmutel@gmail.com)
- Daniel de Koning (d.g.de.koning@cml.leidenuniv.nl)
- Marc van der Meide (m.t.van.der.meide@cml.leidenuniv.nl)

# Copyright
- 2016-2023: Bernhard Steubing (Leiden University)

# License
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
