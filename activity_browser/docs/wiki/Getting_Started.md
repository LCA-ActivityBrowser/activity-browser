# Getting Started

## Installation guide
> [!NOTE]
> If you just want to quickly install Activity Browser, skip to the [Quick installation](#quick-installation) section, 
> if you want a step-by-step guide to install Activity Browser, start here.

### The Anaconda package manager
Skip this step if you already have a working installation of Anaconda or Miniconda, but make sure to keep your 
conda installation up-to-date: `conda update -n base conda`.

You need the python package manager [Anaconda](https://anaconda.org) to install Activity Browser. 
You can install the full [Anaconda user interface (navigator)](https://www.anaconda.com/download/success) 
or just the minimal command-line installer,
[Miniconda](https://docs.anaconda.com/miniconda/#miniconda-latest-installer-links).
If needed, see also the 
[conda user guide](https://docs.conda.io/projects/conda/en/latest/user-guide/index.html) 
or the 
[Conda cheat sheet](https://docs.conda.io/projects/conda/en/latest/_downloads/843d9e0198f2a193a3484886fa28163c/conda-cheatsheet.pdf).

### Add the Conda-Forge channel
The Activity Browser has many dependencies that are managed by the 
[conda-forge](https://conda.io/docs/user-guide/tasks/manage-channels.html) 
channel. 
Open a cmd-window or terminal (in Windows you may have to use the Anaconda prompt) and type the following:
```bash
conda config --prepend channels conda-forge
```

### Installing Activity Browser
You can now install Activity Browser by creating a python environment (`ab`)
```bash
conda create -n ab -c conda-forge activity-browser
```

### Activating and running Activity Browser
To run Activity Browser, you need to activate your environment with 
`conda activate ab` and then run activity browser 
with `activity-browser`.

Congratulations! You've started Activity Browser for the first time!

### Quick installation
You can install and start the activity-browser like this:
1. Install [Miniconda](https://docs.anaconda.com/miniconda/#miniconda-latest-installer-links).
2. ```bash 
   conda create -n ab -c conda-forge activity-browser
   conda activate ab
   activity-browser
   ```

## First steps
### User interface
...

### Understanding Activity Browser terms
Activity Browser uses [Brightway](https://docs.brightway.dev/en/latest/) for its data management and calculations. 
Brightway has its own 'accent' of LCA terms,
you can compare LCA terms from Brightway, [ISO 14044](https://www.iso.org/standard/38498.html) and others in the
[Brightway Glossary](https://docs.brightway.dev/en/latest/content/other/glossary.html).

### Starting Activity Browser
First activate the environment where the activity browser is installed:

```bash
conda activate ab
```

Then simply run `activity-browser` and the application will open.

### Setting up a project
#### Installing a biosphere and impact categories
In the `Project`-tab there is initially a button called `Set up your project with default data`. 
Click this button to add the default data. 
This is equivalent to `brightway2.bw2setup()` in brightway.
You can choose a biosphere version, this biosphere version will be compatible with that version of ecoinvent.
If you don't use ecoinvent, don't worry about this and choose the highest version.

### Importing LCI databases
After adding the default data, you can import a database with the `Import Database` button. 
Follow the instructions of the database import wizard. 
Some special options are:
- [Ecoinvent](https://ecoinvent.org/) is a paid database you can install directly in Activity Browser if you have a 
license and login information.
- [Forwast](http://forwast.brgm.fr/) is a free database you can install directly in Activity Browser.

### Creating your own databases
...

### Running an LCA calculation
...

## Updating Activity Browser
We recommend to regularly update Activity Browser to receive new features & bugfixes. 
These commands will update the Activity Browser and all of its dependencies in the conda environment called `ab`.

```bash
conda activate ab
conda update activity-browser
```

## Need help?
Activity Browser supports its users through the community.
If you have **questions** about using Activity Browser and can't find the answer in this wiki, ask it on our 
[discussions](https://github.com/LCA-ActivityBrowser/activity-browser/discussions) page! 
If you have **found a problem** or have **suggestions to improve** Activity Browser, open an 
[issue](https://github.com/LCA-ActivityBrowser/activity-browser/issues).
If you want to **contribute to the Activity Browser** project, you can check out our 
[contributing](https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/CONTRIBUTING.md)
page to see how you can help out.

## Additional Resources
- [Youtube tutorials](https://www.youtube.com/channel/UCsyySKrzEMsRFsWW1Oz-6aA/)
- [Introduction video by ETH Zurich](https://www.youtube.com/watch?v=j3uLptvsxeA)
- [AB Discussions page](https://github.com/LCA-ActivityBrowser/activity-browser/discussions)
- [AB scientific article](https://doi.org/10.1016/j.simpa.2019.100012)
- The AB has two mailing lists, for [updates](https://brightway.groups.io/g/AB-updates) and [user exchange](https://brightway.groups.io/g/AB-discussion)
- [Brightway2](https://brightway.dev/)
- [Global Sensitiviy Analysis paper](https://onlinelibrary.wiley.com/doi/10.1111/jiec.13194) describing GSA as implemented in the AB; see also our [wiki](https://github.com/LCA-ActivityBrowser/activity-browser/wiki/Global-Sensitivity-Analysis)
- [Modular LCA paper](https://link.springer.com/article/10.1007/s11367-015-1015-3); [documentation modular LCA](http://activity-browser.readthedocs.io/en/latest/index.html); re-implementation of modular LCA into the AB is [ongoing](https://github.com/marc-vdm/activity-browser/tree/mLCA)
