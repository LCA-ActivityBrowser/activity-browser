[![Anaconda-Server Badge](https://anaconda.org/bsteubing/activity-browser/badges/version.svg)](https://anaconda.org/bsteubing/activity-browser)
[![Anaconda-Server Badge](https://anaconda.org/bsteubing/activity-browser/badges/downloads.svg)](https://anaconda.org/bsteubing/activity-browser)
![linux](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/linux.png)
![apple](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/apple.png)
![windows](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/windows.png)
[![Pull request tests](https://github.com/LCA-ActivityBrowser/activity-browser/actions/workflows/main.yaml/badge.svg)](https://github.com/LCA-ActivityBrowser/activity-browser/actions/workflows/main.yaml)
[![Coverage Status](https://coveralls.io/repos/github/LCA-ActivityBrowser/activity-browser/badge.svg?branch=master)](https://coveralls.io/github/LCA-ActivityBrowser/activity-browser?branch=master)


# Activity Browser - a GUI for Brightway2

<img src="https://user-images.githubusercontent.com/33026150/54299977-47a9f680-45bc-11e9-81c6-b99462f84d0b.png" width=100%/>

The activity browser is an open source software for Life Cycle Assessment (LCA) that builds on top of the [Brightway2](https://brightway.dev) LCA framework.

## Highlights

- **Fast LCA calculations** for multiple reference flows and impact categories using [Brightway2](https://brightway.dev) under the hood
- The AB can be used as a **productivity tool for brightway**: you can model in brightway (python) and see the results in the AB or the other way around - whatever is most convenient for you
- **Advanced LCA modeling:**
    - parametrization
    - advanced foreground and background scenario modeling (e.g. possibility to work with scenarios from Integrated Assessment Models)
    - generate and load [presamples](https://github.com/PascalLesage/presamples) data
    - define and directly visualize the uncertainties of your input data (including Pedigree Matrix)
- **Advanced analysis of LCA results:** 
    - Contribution analyses (including aggregation by product name, region or other attributes)
    - Sankey Diagrams
    - Monte Carlo Analysis (building upon the fast brightway engine)
    - Global Sensitivity Analysis
- **Other features**
    - interactively explore supply chains using the graph explorer

## Scientific paper
Please have a look at our scientific paper on the Activity Browser and cite it in your work if it has been useful to you:
https://doi.org/10.1016/j.simpa.2019.100012 

## Youtube tutorials
Watch our videos on [youtube](https://www.youtube.com/channel/UCsyySKrzEMsRFsWW1Oz-6aA/) to learn how to install and use the Activity Browser.

## Contents
- [Installation](#installation)
    - [Conda](#conda)
    - [Configure conda channels](#configure-conda-channels)
    - [Install the activity browser](#install-the-activity-browser)
    - [Updating the activity browser](#updating-the-activity-browser)
    - [Development Version](#development-version)
- [Getting started](#getting-started)
    - [Running the activity browser](#running-the-activity-browser)
    - [Importing an LCI database](#importing-an-lci-database)
- [Contributing](#contributing)
- [Authors](#authors)
- [Copyright](#copyright)
- [License](#authors)
- [Additional Resources](#additional-resources)

## Installation

### Conda

We recommend that you use **conda** to manage your python installation. You can install [Anaconda](https://www.anaconda.com/products/individual) or the more compact [miniconda](https://conda.io/miniconda.html) (Python 3 of course) for your operating system. Installation instructions for miniconda can be found [here](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html). See also the [conda user guide](https://docs.conda.io/projects/conda/en/latest/user-guide/index.html) or the [Conda cheat sheet](https://docs.conda.io/projects/conda/en/latest/_downloads/843d9e0198f2a193a3484886fa28163c/conda-cheatsheet.pdf).

Skip this step if you already have a working installation of anaconda or miniconda, but make sure to keep your conda installation up-to-date: `conda update conda`.

### Configure conda channels

The activity-browser has many dependencies and you need to add five [conda channels](https://conda.io/docs/user-guide/tasks/manage-channels.html) to your configuration file so conda can find all of them. Open a cmd-window or terminal (in Windows you may have to use the Anaconda prompt) and type the following (order is important):

```bash
conda config --append channels conda-forge
conda config --append channels cmutel
conda config --append channels bsteubing
conda config --append channels haasad
conda config --append channels pascallesage
```

If you have already installed brightway2 before, chances are you already have these channels in your config file. You can check your channels with `conda config --show channels`. The output should look something like this if everything is set up correctly:

```bash
channels:
  - defaults
  - conda-forge
  - cmutel
  - bsteubing
  - haasad
  - pascallesage
```

### Install the activity browser

After configuring your conda channels, the activity browser can be installed with this command:

02-06-2021 Currently we are using a different command since there's a different version of MKl we need. 

```bash
conda create -n <Your Environment Name> -c conda-forge -c cmutel -c bsteubing -c haasad -c pascallesage "activity-browser>2.4" mkl=2020.2 python=3.8
```

This will install the activity-browser and all of its dependencies in a new conda environment called `ab`. You can change the environment name `ab` to whatever suits you. Installing for the first time will take a few minutes.

It is recommended that you have a separate conda environment for the activity browser like explained above, but you can also install the activity browser in your root, brightway2 or other existing conda environment if you prefer. Having separate environments for different projects generally reduces unwanted side-effects and incompatibilities between packages. You can still access the same brightway-projects even if you work with different conda environments.

### Updating the activity browser

You may want to update the activity browser to receive new features & bugfixes:

```bash
conda update -n ab --channel conda-forge activity-browser
```

This will update the activity-browser and all of its dependencies in the conda environment called `ab`.

## Development Version
[![Anaconda-Server Badge](https://anaconda.org/bsteubing/activity-browser-dev/badges/version.svg)](https://anaconda.org/bsteubing/activity-browser-dev) [![Anaconda-Server Badge](https://anaconda.org/bsteubing/activity-browser-dev/badges/downloads.svg)](https://anaconda.org/bsteubing/activity-browser-dev)

The most recent version of the master branch is automatically uploaded and generally available via conda ~5 minutes after being committed. Installation is the same as for the stable releases of the activity browser. It is highly advisable to not install the development version in the same conda environment as the stable release (the command `activity-browser` will always start the most recently installed version in a given environment).

Install the development version like this:

```bash
conda create -y -n ab_dev -c conda-forge -c cmutel -c bsteubing -c haasad -c pascallesage "activity-browser-dev>2019.10.30"
```

Or update like this if you already have a dev environment:

```bash
conda activate ab_dev
conda update --channel conda-forge activity-browser-dev
```

---

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

## Authors
- Bernhard Steubing (b.steubing@cml.leidenuniv.nl)
- Daniel de Koning (d.g.de.koning@cml.leidenuniv.nl)
- Adrian Haas (haasad@ethz.ch)
- Chris Mutel (cmutel@gmail.com)

## Contributing projects
The development of the Activity Browser was co-financed by the following projects:
- Life Cycle Management of wood in Switzerland (Swiss National Science Foundation, NRP 66 Resource Wood project number 136623)
- MIN-TEA (Materials Innovative Technologies Assessment; EIT Raw Materials project number 18231)

## Copyright
- 2017-2020: Bernhard Steubing and Daniel de Koning (Leiden University), Adrian Haas (ETH Zurich)
- 2016: Chris Mutel and Paul Scherrer Institut
- 2015: Bernhard Steubing and ETH Zurich

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

__Activity Browser__:
- paper on the Activity Browser: https://doi.org/10.1016/j.simpa.2019.100012
- paper on modular LCA using the Activity Browser: https://link.springer.com/article/10.1007/s11367-015-1015-3
- documentation modular LCA: http://activity-browser.readthedocs.io/en/latest/index.html
- version of the AB that includes modular LCA: https://bitbucket.org/bsteubing/activity-browser

__Brightway2__:
- https://brightway.dev/
