# Activity Browser - a graphical interface for Brightway2

Copyright (c) 2015, Bernhard Steubing and ETH Zurich
Copyright (c) 2016, Chris Mutel and Paul Scherrer Institut
Copyright (c) 2017, Adrian Haas and ETH Zurich

Licensed under the GNU General Public License.

- Note that this is a *hard* fork of Bernhard Steubing's work, and does not preserve compatibility.
- This is a fork of Chris Mutel's version of the activity-browser on [bitbucket](https://bitbucket.org/cmutel/activity-browser)
- The original repo was converted from mercurial to git using [fast-export](https://github.com/frej/fast-export)  

## Installation

### Miniconda

Install the newest python 3 version of [miniconda](https://conda.io/miniconda.html) for your operating system. Detailed installation instructions for miniconda can be found [here](https://conda.io/docs/user-guide/install/index.html).

Skip this step if you already have a working installation of anaconda or miniconda.

### Configure conda channels

The activity-browser has many dependencies and you need to add three [conda channels](https://conda.io/docs/user-guide/tasks/manage-channels.html) to your configuration file so conda can find all of them. Open a cmd-window or terminal and type the following (order is important):
```
conda config --append channels conda-forge
conda config --append channels cmutel
conda config --append channels haasad
```
If you have already installed brightway2 before and followed eg. the instructions from the ESDwiki, chances are you already have these channels in your config file. You can check your channels with `conda config --show` or `conda config --key channels`.

### Install the activity browser

After configuring your conda channels, the activity browser can be installed with this command:
```
conda create --yes --name ab activity-browser
```
This will install the activity-browser and all of its dependencies in a new conda environment called `ab`. You can change the environment name `ab` to whatever suits you. Installing for the first time will take a few minutes.

### Run the activity browser

First activate the environment where the activity browser is installed:
- Windows: `activate ab`
- Unix: `source activate ab`

Then simply run `activity-browser` and the application will open.
