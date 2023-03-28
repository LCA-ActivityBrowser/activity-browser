[![conda-forge version](https://img.shields.io/conda/vn/conda-forge/activity-browser.svg)](https://anaconda.org/conda-forge/activity-browser)
[![bsteubing version](https://img.shields.io/conda/vn/bsteubing/activity-browser.svg)](https://anaconda.org/bsteubing/activity-browser)
[![Downloads](https://anaconda.org/conda-forge/activity-browser/badges/downloads.svg)](https://anaconda.org/conda-forge/activity-browser)
![linux](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/linux.png)
![apple](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/apple.png)
![windows](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/windows.png)
[![Pull request tests](https://github.com/LCA-ActivityBrowser/activity-browser/actions/workflows/main.yaml/badge.svg)](https://github.com/LCA-ActivityBrowser/activity-browser/actions/workflows/main.yaml)
[![Coverage Status](https://coveralls.io/repos/github/LCA-ActivityBrowser/activity-browser/badge.svg?branch=master)](https://coveralls.io/github/LCA-ActivityBrowser/activity-browser?branch=master)


# Activity Browser - a GUI for Brightway2

<img src="https://user-images.githubusercontent.com/33026150/54299977-47a9f680-45bc-11e9-81c6-b99462f84d0b.png" width=100%/>

The Activity Browser is an open source software for Life Cycle Assessment (LCA) that builds on [Brightway2](https://brightway.dev).

Our [scientific paper](https://doi.org/10.1016/j.simpa.2019.100012) on the Activity Browser. Please cite it in your work!

Watch our videos on the AB on [youtube](https://www.youtube.com/channel/UCsyySKrzEMsRFsWW1Oz-6aA/).

## Contents
- [Hightlights](#highlights)
- [Quickstart](#quickstart)
- [Installation](#installation)
    - [Conda](#conda)
    - [Install the activity browser with Ecoinvent >=3.9](#install-activity-browser-with-ecoinvent-39)
    - [Install the activity browser with Ecoinvent <3.9](#install-activity-browser-with-older-ecoinvent-versions-39)
    - [Updating the activity browser](#updating-the-activity-browser)
- [Getting started](#getting-started)
    - [Running the activity browser](#running-the-activity-browser)
    - [Importing an LCI database](#importing-an-lci-database)
- [Contributing](#contributing)
- [Developers](#developers)
- [Copyright](#copyright)
- [License](#license)
- [Additional Resources](#additional-resources)

## Highlights

- **Fast LCA calculations** 
    - for multiple reference flows, impact categories, and scenarios
- **A productivity tool for brightway**: 
    - model in brightway (python) and see the results in the AB or vice-versa 
- **Advanced modeling:**
    - Parameters
    - Scenarios (e.g. prospective LCI databases from [premise](https://premise.readthedocs.io/en/latest/))
    - Uncertainties
    - Use the Graph Explorer to understand supply chains
- **Advanced analysis of LCA results:**
    - Advanced contribution analysis
    - Sankey Diagrams
    - Monte Carlo and Global Sensitivity Analysis

## Quickstart

You can install and start the activity-browser like this:

```bash
conda create -n ab -c conda-forge activity-browser
conda activate ab
activity-browser
```

## Installation

### Conda

We recommend that you use **conda** to manage your python installation. You can install [Anaconda](https://www.anaconda.com/products/individual) or the more compact [miniconda](https://conda.io/miniconda.html) (Python 3 of course) for your operating system. Installation instructions for miniconda can be found [here](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html). See also the [conda user guide](https://docs.conda.io/projects/conda/en/latest/user-guide/index.html) or the [Conda cheat sheet](https://docs.conda.io/projects/conda/en/latest/_downloads/843d9e0198f2a193a3484886fa28163c/conda-cheatsheet.pdf).

Skip this step if you already have a working installation of anaconda or miniconda, but make sure to keep your conda installation up-to-date: `conda update conda`.

#### Add the Conda-Forge channel
The activity-browser has many dependencies that are managed by the conda-forge [channel](https://conda.io/docs/user-guide/tasks/manage-channels.html). Open a cmd-window or terminal (in Windows you may have to use the Anaconda prompt) and type the following:

```bash
conda config --prepend channels conda-forge
```
### Install Activity-Browser with Ecoinvent >=3.9
After prepending the Conda-Forge channel the following line should be executed within the command prompt/terminal to install the Activity-Browser and it's dependencies.

```bash
conda create -n ab activity-browser
```
This will install the Activity-Browser with the latest version of the Brightway2 libraries (currently excluding Brightway2.5 libraries).

### Install Activity-Browser with older Ecoinvent versions (<3.9)

If you want to run the Activity Browser with older versions of ecoinvent (<3.9) a different Biosphere3 database needs to be installed. This requires a _**different version of the bw2io library**_. Thus, to work with ecoinvent versions < 3.9, the following additional commands need to be executed. Note that this will lead to a virtual environment that can then ONLY work with version < 3.9. If you want to work with version > 3.9 AND < 3.9, the only solution currently available is to use two separate virtual environments (AB installations).

For a new installation from the conda-forge repository the same initial steps need to be made: Prepending the Conda-Forge repository in the channels, and installing the Activity-Browser and dependencies. After the successful installation, thse two further commands need to be executed before running the Activity-Browser: <i>1)</i> Remove the latest version of the Brightway2 Input-Output library, <i>2)</i> Install an older version of the Brightway2 Input-Output library.

```bash
conda remove --force bw2io
conda install bw2io=0.8.7
```

#### Activity-Browser is installed

At this point the activity-browser and all of its dependencies will be installed in a new conda environment called `ab`. You can change the environment name `ab` to whatever suits you. (Note, Installing for the first time will take a few minutes).

### Updating the activity browser

You may want to update the activity browser to receive new features & bugfixes:

```bash
conda activate ab
conda update activity-browser
```

This will update the activity-browser and all of its dependencies in the conda environment called `ab`.

| :warning: The activity browser has dropped support for python versions below `3.8`|
|---|
| You should re-install if you have an older installation of the activity browser which doesn't use `python >= 3.8` (you can check with `conda list` or `python --version` in your conda environment). You can remove your existing environment with `conda remove -n ab --all` or choose a new environment name (instead of `ab`). Re-installing will not affect your activity-browser/brightway projects. |

## Getting started

**Watch our videos on [youtube](https://www.youtube.com/channel/UCsyySKrzEMsRFsWW1Oz-6aA/) on how to install and use the Activity Browser and/or read below and in our [Wiki](https://github.com/LCA-ActivityBrowser/activity-browser/wiki).**

### Running the activity browser

First activate the environment where the activity browser is installed:

```bash
conda activate ab
```

Then simply run `activity-browser` and the application will open.

### Importing an LCI database

- In the `inventory`-tab there is a button called _"Add default data (biosphere flows and impact categories)"_. Click this button to add the default data. This is equivalent to `brightway2.bw2setup()` in python.
- After adding the default data, you can import a database with the _"Import Database"_-Button. Follow the instructions of the database import wizard. There are currently three types of imports possible:
    - Directly from the ecoinvent homepage (ecoinvent login credentials required)
    - From a 7zip archive
    - From a directory with ecospold2 files (same as in brightway2)

## Contributing

**Your contribution counts! The AB is a community project.**

If you have ideas for improvements to the code or documentation or want to propose new features, please take a look at our [contributing guidelines](CONTRIBUTING.md) and open issues and/or pull-requests.

If you experience problems or are suffering from a specific bug, please [raise an issue](https://github.com/LCA-ActivityBrowser/activity-browser/issues) here on github.

## Developers

#### Current main developers

- Bernhard Steubing (b.steubing@cml.leidenuniv.nl) (creator)
- Jonathan Kidner (j.h.kidner@cml.leidenuniv.nl) (lead developer)

#### Important contributers

- Adrian Haas (haasad@ethz.ch)
- Chris Mutel (cmutel@gmail.com)
- Daniel de Koning (d.g.de.koning@cml.leidenuniv.nl)
- Marc van der Meide (m.t.van.der.meide@cml.leidenuniv.nl)

## Copyright
- 2016-2023: Bernhard Steubing (Leiden University)

## License
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

## Additional Resources

- [Scientific paper](https://doi.org/10.1016/j.simpa.2019.100012)
- [Youtube tutorials](https://www.youtube.com/channel/UCsyySKrzEMsRFsWW1Oz-6aA/)
- [AB Wiki](https://github.com/LCA-ActivityBrowser/activity-browser/wiki)
- [Brightway2](https://brightway.dev/)
- Global Sensitiviy Analysis: [paper](https://onlinelibrary.wiley.com/doi/10.1111/jiec.13194) describing GSA as implemented in the AB; see also our [wiki](https://github.com/LCA-ActivityBrowser/activity-browser/wiki/Global-Sensitivity-Analysis)
- Modular LCA: paper on [modular LCA](https://link.springer.com/article/10.1007/s11367-015-1015-3) using the AB; [documentation modular LCA](http://activity-browser.readthedocs.io/en/latest/index.html); re-implementation of modular LCA into the AB is ongoing, see [here](https://github.com/marc-vdm/activity-browser/tree/mLCA)
