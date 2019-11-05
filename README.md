[![Anaconda-Server Badge](https://anaconda.org/bsteubing/activity-browser/badges/version.svg)](https://anaconda.org/bsteubing/activity-browser) [![Anaconda-Server Badge](https://anaconda.org/bsteubing/activity-browser/badges/downloads.svg)](https://anaconda.org/bsteubing/activity-browser)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;![linux](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/linux.png)![apple](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/apple.png)[![Build Status](https://travis-ci.org/LCA-ActivityBrowser/activity-browser.svg?branch=master)](https://travis-ci.org/LCA-ActivityBrowser/activity-browser)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;![windows](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/windows.png)[![Build status](https://ci.appveyor.com/api/projects/status/8cljoh7o1jrof8tf/branch/master?svg=true)](https://ci.appveyor.com/project/bsteubing/activity-browser/branch/master)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[![Coverage Status](https://coveralls.io/repos/github/LCA-ActivityBrowser/activity-browser/badge.svg?branch=master)](https://coveralls.io/github/LCA-ActivityBrowser/activity-browser?branch=master)



# Activity Browser - a GUI for Brightway2

<img src="https://user-images.githubusercontent.com/33026150/54299977-47a9f680-45bc-11e9-81c6-b99462f84d0b.png" width=100%/>

The activity browser is a graphical user interface for the [Brightway2](https://brightwaylca.org) advanced life cycle
assessment framework, making use of `Qt` through `Qt for Python` under the [LGPLv3 license](https://www.gnu.org/licenses/lgpl-3.0.html).

- [Installation](#installation)
    - [Miniconda](#miniconda)
    - [Configure conda channels](#configure-conda-channels)
    - [Install the activity browser](#install-the-activity-browser)
    - [Run the the activity browser](#run-the-activity-browser)
    - [Import an LCI database](#import-an-lci-database)
- [Development Version](#development-version)
    - [PyQt5 vs PySide2](#pyqt5-vs-pyside2)
    - [Updating to PySide2](#updating-to-pyside2)
- [Contributing](#contributing)
- [Additional Resources](#additional-resources)
- [Authors](#authors)


## Installation

### Miniconda

Install the newest python 3 version of [miniconda](https://conda.io/miniconda.html) for your operating system. Detailed installation instructions for miniconda can be found [here](https://conda.io/docs/user-guide/install/index.html).

Skip this step if you already have a working installation of anaconda or miniconda, but make sure to keep your conda installation up-to-date: `conda update conda`.

### Configure conda channels

The activity-browser has many dependencies and you need to add four [conda channels](https://conda.io/docs/user-guide/tasks/manage-channels.html) to your configuration file so conda can find all of them. Open a cmd-window or terminal and type the following (order is important):

```bash
conda config --append channels conda-forge
conda config --append channels cmutel
conda config --append channels bsteubing
conda config --append channels haasad
```

If you have already installed brightway2 before, chances are you already have these channels in your config file. You can check your channels with `conda config --show channels`. The output should look something like this if everything is set up correctly:

```bash
channels:
  - defaults
  - conda-forge
  - cmutel
  - bsteubing
  - haasad
```

### Install the activity browser

After configuring your conda channels, the activity browser can be installed with this command:

```bash
conda create --yes --name ab --channel conda-forge activity-browser
```

This will install the activity-browser and all of its dependencies in a new conda environment called `ab`. You can change the environment name `ab` to whatever suits you. Installing for the first time will take a few minutes.

It is recommended that you have a separate conda environment for the activity browser like explained above, but you can also install the activity browser in your root, brightway2 or other existing conda environment if you prefer. Having separate environments for different projects generally reduces unwanted side-effects and incompatibilities between packages. You can still access the same brightway-projects even if you work with different conda environments.

### Run the activity browser

First activate the environment where the activity browser is installed:

```bash
conda activate ab
```

Then simply run `activity-browser` and the application will open.

### Import an LCI database

- In the `inventory`-tab there is a button called _"Add Default Data (Biosphere flows, LCIA methods)"_. Click this button to add the default data. This is equivalent to `brightway2.bw2setup()` in python.
- After adding the default data, you can import a database with the _"Import Database"_-Button. Follow the instructions of the database import wizard. There are currently three types of imports possible:
    - Directly from the ecoinvent homepage (ecoinvent login credentials required)
    - From a 7zip archive
    - From a directory with ecospold2 files (same as in brightway2)


## Development Version
[![Anaconda-Server Badge](https://anaconda.org/bsteubing/activity-browser-dev/badges/version.svg)](https://anaconda.org/bsteubing/activity-browser-dev) [![Anaconda-Server Badge](https://anaconda.org/bsteubing/activity-browser-dev/badges/downloads.svg)](https://anaconda.org/bsteubing/activity-browser-dev)

### PyQt5 vs PySide2

The newest builds after 2019-11-04 for the activity browser makes use of PySide2 instead of PyQt5. This change made due
to a number of reasons, most importantly:

- PyQt5 [requires](https://www.riverbankcomputing.com/static/Docs/PyQt5/introduction.html#license) that the Activity
Browser uses the GPL license, where PySide2 [allows](https://doc.qt.io/qtforpython/licenses.html#licenses-used-in-qt-for-python)
the Activity Browser to use a more permissive license.
  - Activity Browser is now published under the LGPL license, if a more permissive license is needed, please contact the developers.
- PySide2 is maintained and developed by [The Qt Company](https://groups.google.com/forum/#!topic/pyside-dev/pqwzngAGLWE),
and deemed more likely to be future-proof.

### Updating to PySide2

In order to update the conda environment for the Activity Browser one of three different options can be used:

1. Create a new environment entirely
    ```bash
    conda create -n new_ab_dev -c conda-forge -c cmutel -c bsteubing -c haasad activity-browser-dev
    ```
2. Remove PyQt5 and install PySide2
    ```bash
    # Remove only the 'pyqt', 'matplotlib' and 'seaborn' packages
    conda remove --force pyqt matplotlib seaborn
    # Install the replacements from the conda-forge channel
    conda install -c conda-forge pyside2 matplotlib-base seaborn
    ```
3. (Not recommended) Install PySide2 next to PyQt5
    ```bash
    # Will sometimes work, causes issues other times.
    conda install pyside2
    ```

The most recent version of the master branch is automatically uploaded and generally available via conda ~5 minutes after being committed. Installation is the same as for the stable releases of the activity browser. It is highly advisable to not install the development version in the same conda environment as the stable release (the command `activity-browser` will always start the most recently installed version in a given environment).

Install the development version like this:

```bash
conda create --yes --name ab_dev --channel conda-forge activity-browser-dev
```

Or update like this if you already have a dev environment:

```bash
conda activate ab_dev
conda update --channel conda-forge activity-browser-dev
```

## Contributing

If you have ideas for improvements to the code or documentation or want to propose new features, don't hesitate to look at our [contributing guidelines](CONTRIBUTING.md) and open issues and/or pull-requests.

If you experience problems or are suffering from a specific bug, please [raise an issue](https://github.com/LCA-ActivityBrowser/activity-browser/issues) here on github.


## Additional Resources

__Activity Browser__:
- https://bitbucket.org/bsteubing/activity-browser  (first version)
- http://activity-browser.readthedocs.io/en/latest/index.html  (documentation modular LCA)
- https://link.springer.com/article/10.1007/s11367-015-1015-3  (paper modular LCA / streamlining scenario analysis)

__Brightway2__:
- https://bitbucket.org/cmutel/brightway2
- https://brightwaylca.org/
- https://github.com/PoutineAndRosti/Brightway-Seminar-2017  (good starting point for learning bw)


## Authors

- Bernhard Steubing (b.steubing@cml.leidenuniv.nl)
- Adrian Haas (haasad@ethz.ch)
- Chris Mutel (cmutel@gmail.com)
- Daniel de Koning (d.g.de.koning@cml.leidenuniv.nl)


## Copyright
Copyright (c) 2017-2019, Bernhard Steubing (Leiden University), Adrian Haas (ETH Zurich)
Copyright (c) 2016, Chris Mutel and Paul Scherrer Institut
Copyright (c) 2015, Bernhard Steubing and ETH Zurich



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
