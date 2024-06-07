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

[Video tutorials](https://www.youtube.com/channel/UCsyySKrzEMsRFsWW1Oz-6aA/) are available on youtube.

Please also read and cite our [scientific paper](https://doi.org/10.1016/j.simpa.2019.100012).


### Some highlights

- **Fast LCA calculations**: for multiple reference flows, impact categories, and scenarios
- **A productivity tool for brightway**: model in brightway (python) and see the results in the AB or vice-versa
- **Advanced modeling:** Use parameters, scenarios (including prospective LCI databases from [premise](https://premise.readthedocs.io/en/latest/)), uncertainties and our Graph Explorer
- **Advanced analyses:** Contribution analyses, Sankey Diagrams, Monte Carlo, and Global Sensitivity Analysis

# Contents
- [Installation](#installation)
- [Updating the AB](#updating-the-ab)
- [Getting started](#getting-started)
    - [Running the AB](#running-the-ab)
    - [Importing LCI databases](#importing-lci-databases)
    - [Additional Resources](#additional-resources)
- [Plugins](#plugins)
    - [Available plugins](#available-plugins)
    - [Installation](#installation-1)
    - [Usage](#usage)
    - [Development](#development)
- [Contributing](#contributing)
- [Developers](#developers)
- [Copyright](#copyright)
- [License](#license)

# Installation

## The quick way

You can install and start the activity-browser like this:

```bash
conda create -n ab -c conda-forge --solver libmamba activity-browser
conda activate ab
activity-browser
```

### Mamba

You can also install the AB using [Mamba](https://mamba.readthedocs.io/en/latest/mamba-installation.html#mamba-install):

```bash
mamba create -n ab activity-browser
mamba activate ab
activity-browser
```

## The thorough way
### Conda

We recommend that you use **conda** to manage your python installation. You can install [Anaconda](https://www.anaconda.com/products/individual) or the more compact [miniconda](https://conda.io/miniconda.html) (Python 3 version) for your operating system. Installation instructions for miniconda can be found [here](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html). See also the [conda user guide](https://docs.conda.io/projects/conda/en/latest/user-guide/index.html) or the [Conda cheat sheet](https://docs.conda.io/projects/conda/en/latest/_downloads/843d9e0198f2a193a3484886fa28163c/conda-cheatsheet.pdf).

Skip this step if you already have a working installation of anaconda or miniconda, but make sure to keep your conda installation up-to-date: `conda update -n base conda`.

### Add the Conda-Forge channel
The activity-browser has many dependencies that are managed by the [conda-forge](https://conda.io/docs/user-guide/tasks/manage-channels.html) channel. Open a cmd-window or terminal (in Windows you may have to use the Anaconda prompt) and type the following:

```bash
conda config --prepend channels conda-forge
```
Also configure conda to use the libmamba solver which is significantly faster than the default.
```bash
conda config --set solver libmamba
```

### Installing Activity Browser

```bash
conda create -n ab -c conda-forge activity-browser
conda activate ab
activity-browser
```

#### Activity Browser is installed

At this point the activity-browser and all of its dependencies will be installed in a new conda environment called `ab`. You can change the environment name `ab` to whatever suits you.

## Updating the AB

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
- [Introduction video by ETH Zurich](https://www.youtube.com/watch?v=j3uLptvsxeA)
- [AB Discussions page](https://github.com/LCA-ActivityBrowser/activity-browser/discussions)
- [AB Wiki](https://github.com/LCA-ActivityBrowser/activity-browser/wiki)
- [AB scientific article](https://doi.org/10.1016/j.simpa.2019.100012)
- The AB has two mailing lists, for [updates](https://brightway.groups.io/g/AB-updates) and [user exchange](https://brightway.groups.io/g/AB-discussion)
- [Brightway2](https://brightway.dev/)
- [Global Sensitiviy Analysis paper](https://onlinelibrary.wiley.com/doi/10.1111/jiec.13194) describing GSA as implemented in the AB; see also our [wiki](https://github.com/LCA-ActivityBrowser/activity-browser/wiki/Global-Sensitivity-Analysis)
- [Modular LCA paper](https://link.springer.com/article/10.1007/s11367-015-1015-3); [documentation modular LCA](http://activity-browser.readthedocs.io/en/latest/index.html); re-implementation of modular LCA into the AB is [ongoing](https://github.com/marc-vdm/activity-browser/tree/mLCA)

# Plugins
| :warning: DISCLAIMER                                                                                                                                                                  |
|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Plugins are not necessarily developed by Activity Browser maintainers. Below are listed plugins from people we trust but we do not check plugins code. **Use them at your own risk**. |
| The plugin system is still in development so keep in mind that things may change at any point.                                                                                        |

Since the `2.8 release` a plugin system has been added to the AB. Plugins are a flexible way to add new functionalities to the AB without modifying the software itself.

The plugin code has been designed and written by Remy le Calloch (supported by [G-SCOP laboratories](https://g-scop.grenoble-inp.fr/en/laboratory/g-scop-laboratory)) with revisions from the AB-team.


## Available plugins

These are the plugins that we know about. To add your plugin to this list either open an issue, or a pull request. All submitted plugins will be reviewed, although all risks associated with their use shall be born by the user.

| Name     | Description | Links | Author(s) |
|:---------|-------------|-------|-----------|
| [ScenarioLink](https://github.com/polca/ScenarioLink) | Enables you to seamlessly fetch and reproduce scenario-based LCA databases, such as those generated by [premise](https://github.com/polca/premise) | [anaconda](https://anaconda.org/romainsacchi/ab-plugin-scenariolink), [pypi](https://pypi.org/project/ab-plugin-scenariolink/), [github](https://github.com/polca/ScenarioLink) | Romain Sacchi & Marc van der Meide |
| [ReSICLED](https://github.com/Pan6ora/ab-plugin-ReSICLED) | Evaluating the recyclability of electr(on)ic product for improving product design | [anaconda](https://anaconda.org/pan6ora/ab-plugin-resicled), [github](https://github.com/Pan6ora/ab-plugin-ReSICLED) | G-SCOP Laboratory |
| [Notebook](https://github.com/Pan6ora/ab-plugin-Notebook) | Use Jupyter notebooks from AB | [anaconda](https://anaconda.org/pan6ora/ab-plugin-template), [github](https://github.com/Pan6ora/ab-plugin-Notebook) | Rémy Le Calloch |
| [template](https://github.com/Pan6ora/activity-browser-plugin-template) | An empty plugin to start from | [anaconda](https://anaconda.org/pan6ora/ab-plugin-template), [github](https://github.com/Pan6ora/activity-browser-plugin-template) | Rémy Le Calloch |

## Installation

### detailed instructions

Every plugin's Github page (links are provided in the above table) should have a **Get this plugin** section with installation instructions.

### general instructions

Plugins are conda packages (like the Activity Browser). To add a plugin simply install it in your conda environment from the Anaconda repos.

_Nb: add `-c conda-forge` to the install command like below to avoid problems with dependencies._

Ex:

```
conda activate ab
conda install -c pan6ora -c conda-forge ab-plugin-notebook
```

## Usage

Once a new plugin is installed restart the Activity Browser.

### enabling a plugin

Plugins are enabled **per-project**. Simply open the plugin manager in the `Tools > Plugins` menu.

Close the plugin manager. New tabs should have appeared in the AB (each plugin can spawn one tab on each left/right panel).

### disabling a plugin

Disable a plugin the same way you activated it.

**:warning: Keep in mind that all data created by the plugin in a project could be erased when you disable it.**

## Development

The best place to start to create new plugins is the [plugin template](https://github.com/Pan6ora/activity-browser-plugin-template). Its code and README will help you to understand how to create a plugin.

# Contributing

**The Activity Browser is a community project. Your contribution counts!**

If you have ideas for improvements to the code or documentation or want to propose new features, please take a look at our [contributing guidelines](CONTRIBUTING.md) and open issues and/or pull-requests.

If you experience problems or are suffering from a specific bug, please [raise an issue](https://github.com/LCA-ActivityBrowser/activity-browser/issues) here on github.

# Developers

### Current main developers

- Bernhard Steubing (b.steubing@cml.leidenuniv.nl) (creator)
- Marin Visscher (m.r.visscher@cml.leidenuniv.nl) (main developer)
- Marc van der Meide (m.t.van.der.meide@cml.leidenuniv.nl) (maintainer)

### Important contributers

- [Adrian Haas](https://github.com/haasad)
- [Chris Mutel](https://github.com/cmutel)
- [Daniel de Koning](https://github.com/dgdekoning)
- [Jonathan Kidner](https://github.com/Zoophobus)
- [Remy le Calloch](https://remy.lecalloch.net)

# Copyright
- 2016-2023: Bernhard Steubing (Leiden University)

# License
You can find the license information for Activity Browser in the [license file](https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/LICENSE.txt).
