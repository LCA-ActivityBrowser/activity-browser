[![Anaconda-Server Badge](https://anaconda.org/haasad/activity-browser/badges/version.svg)](https://anaconda.org/haasad/activity-browser) [![Anaconda-Server Badge](https://anaconda.org/haasad/activity-browser/badges/downloads.svg)](https://anaconda.org/haasad/activity-browser)

# Activity Browser - a GUI for Brightway2

<img src="https://user-images.githubusercontent.com/11636405/33426133-156c61ce-d5c1-11e7-8017-2a5763a5b265.png" width="250"/><img src="https://user-images.githubusercontent.com/11636405/33426139-1d1ca7a8-d5c1-11e7-819b-c4ceb2da310a.png" width="250"/><img src="https://user-images.githubusercontent.com/11636405/33426144-1fe288e0-d5c1-11e7-825f-9aedd64071b0.png" width="250"/>

The activity browser is a graphical user interface for the [Brightway2](https://brightwaylca.org) advanced life cycle assessment framework.

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

## Info

- Note that this is a *hard* fork of Bernhard Steubing's work, and does not preserve compatibility.
- This is a fork of Chris Mutel's version of the activity-browser on [bitbucket](https://bitbucket.org/cmutel/activity-browser)
- The original repo was converted from mercurial to git using [fast-export](https://github.com/frej/fast-export)  

## Additional Resources

__Activity Browser__:
- https://bitbucket.org/bsteubing/activity-browser  (first version)
- http://activity-browser.readthedocs.io/en/latest/index.html  (documentation modular LCA)
- https://link.springer.com/article/10.1007/s11367-015-1015-3  (paper modular LCA / streamlining scenario analysis)

__Brightway2__:
- https://bitbucket.org/cmutel/brightway2
- https://brightwaylca.org/
- https://github.com/PoutineAndRosti/Brightway-Seminar-2017  (good starting point for learning bw)
