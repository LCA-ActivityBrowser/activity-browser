[![Anaconda-Server Badge](https://anaconda.org/haasad/activity-browser/badges/version.svg)](https://anaconda.org/haasad/activity-browser) [![Anaconda-Server Badge](https://anaconda.org/haasad/activity-browser/badges/downloads.svg)](https://anaconda.org/haasad/activity-browser)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;![linux](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/linux.png)![apple](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/apple.png)[![Build Status](https://travis-ci.org/LCA-ActivityBrowser/activity-browser.svg?branch=master)](https://travis-ci.org/LCA-ActivityBrowser/activity-browser)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;![windows](https://raw.githubusercontent.com/vorillaz/devicons/master/!PNG/windows.png)[![Build status](https://ci.appveyor.com/api/projects/status/8cljoh7o1jrof8tf/branch/master?svg=true)](https://ci.appveyor.com/project/haasad/activity-browser/branch/master)



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

It is recommended that you have a separate conda environment for the activity browser like explained above, but you can also install the activity browser in your root, brightway2 or other existing conda environment if you prefer. Having separate environments for different projects generally reduces unwanted side-effects and incompatibilities between packages. You can still access the same brightway-projects even if you work with different conda environments.

### Run the activity browser

First activate the environment where the activity browser is installed:
- Windows: `activate ab`
- Unix: `source activate ab`

Then simply run `activity-browser` and the application will open.

### Import an LCI database

- In the `inventory`-tab there is a button called _"Add Default Data (Biosphere flows, LCIA methods)"_. Click this button to add the default data. This is equivalent to `brightway2.bw2setup()` in python.
- After adding the default data, you can import a database with the _"Import Database"_-Button. Follow the instructions of the database import wizard. There are currently three types of imports possible:
    - Directly from the ecoinvent homepage (ecoinvent login credentials required)
    - From a 7zip archive
    - From a directory with ecospold2 files (same as in brightway2)


## Development Version
[![Anaconda-Server Badge](https://anaconda.org/haasad/activity-browser-dev/badges/version.svg)](https://anaconda.org/haasad/activity-browser-dev) [![Anaconda-Server Badge](https://anaconda.org/haasad/activity-browser-dev/badges/downloads.svg)](https://anaconda.org/haasad/activity-browser-dev)

The most recent version of the master branch is automatically uploaded and generally available via conda ~5 minutes after being committed. Installation is the same as for the stable releases of the activity browser. It is highly advisable to not install the development version in the same conda environment as the stable release (the command `activity-browser` will always start the most recently installed version in a given environment).

Install the development version like this:
```
conda create --yes --name ab_dev activity-browser-dev
```
Or update like this if you already have a dev environment:
```
activate ab_dev # win
source activate ab_dev # linux, osx
conda update activity-browser-dev
```

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
