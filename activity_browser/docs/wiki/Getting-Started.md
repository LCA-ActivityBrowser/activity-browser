# Installation guide
> [!NOTE]
> If you just want to quickly install Activity Browser, skip to the [Quick installation](#quick-installation) section, 
> if you want a step-by-step guide to install Activity Browser, start here.

## The Anaconda package manager
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

## Add the Conda-Forge channel
The Activity Browser has many dependencies that are managed by the 
[conda-forge](https://conda.io/docs/user-guide/tasks/manage-channels.html) 
channel. 
Open a cmd-window or terminal (in Windows you may have to use the Anaconda prompt) and type the following:
```bash
conda config --prepend channels conda-forge
```

## Installing Activity Browser
You can now install Activity Browser by creating a python environment (`ab`)
```bash
conda create -n ab -c conda-forge activity-browser
```

## Activating and running Activity Browser
To run Activity Browser, you need to activate your environment with 
`conda activate ab` and then run activity browser 
with `activity-browser`.

Congratulations! You've started Activity Browser for the first time!

## Quick installation
You can install and start the activity-browser like this:
1. Install [Miniconda](https://docs.anaconda.com/miniconda/#miniconda-latest-installer-links).
2. ```bash 
   conda create -n ab -c conda-forge activity-browser
   conda activate ab
   activity-browser
   ```

# Updating Activity Browser
We recommend to regularly update Activity Browser to receive new features & bugfixes. 
These commands will update the Activity Browser and all of its dependencies in the conda environment called `ab`.

```bash
conda activate ab
conda update activity-browser
```

# First steps
## Starting Activity Browser
First activate the environment where the activity browser is installed:

```bash
conda activate ab
```

Then simply run `activity-browser` and the application will open.

## Understanding Activity Browser terms
Activity Browser uses [Brightway](https://docs.brightway.dev/en/latest/) for its data management and calculations. 
Brightway has its own 'accent' of LCA terms,
you can compare LCA terms from Brightway, [ISO 14044 (2006)](https://www.iso.org/standard/38498.html) and others in the
[Brightway Glossary](https://docs.brightway.dev/en/latest/content/other/glossary.html).

## Organization of data in Brightway and Activity Browser
Data in Brightway is organized into projects
- Projects contain databases, impact categories, calculation setups and more
  - Databases contain activities (biosphere and technosphere)
    - Activities are the building blocks of your LCA model 
- Impact categories are used to score your LCA models against
- Calculation setups are the combinations of reference flows and impact categories that you can calculate
- Projects also contain other data, such as parameters and plugin settings.

Read more about how data is organized in the 
[Brightway documentation](https://docs.brightway.dev/en/latest/content/theory/structure.html#brightway-objects).

## User interface
Activity Browser is organized in two panels, which themselves have tabs and a menu bar. 
The left panel has a `Project` tab and an `Impact Categories` tab.
The right panel has the `Welcome` screen, `LCA setup` tab, `Parameters` tab and -if used- an `LCA Results` tab.

The [`Project`](Projects) tab shows your current project, the databases in that project and the contents of a database if it is open.
The [`Impact Categories`](Impact-Categories) tab shows all impact categories that are installed in the current project.
The [`LCA Setup`](LCA-Calculation-Setups) tab allows you to define reference flows, impact categories and scenarios for calculations.
The [`Parameters`](Parameters) tab allows you to manage your parameters.
The [`LCA Results`](LCA-Results) tab shows the results of the calculations you do.
Finally, the menu bar at the top allows you to manage Activity Browser, Plugins and Project settings.

## Setting up a project
### Installing a biosphere and impact categories
**... reorder this section when screenshots are available**

In the `Project`-tab there is initially a button called `Set up your project with default data`. 
Click this button to add the default data. 
This adds a `biosphere` database which contains a number of standardized biosphere flows.

> [!NOTE]
> Once a project is set up, you cannot reset it.

**... screenshot of first dialog page**

#### Setting up with Biosphere3 data
You can choose a biosphere version, this biosphere version will be compatible with that version of ecoinvent, 
if you choose to import that later.
If you don't use ecoinvent, don't worry about this and choose the highest version.

**... screenshot of relevant dialog**

#### Setting up with ecoinvent data
If you have a valid ecoinvent license and login information, you can immediately set up ecoinvent in your project with all 
relevant and compatible data. 

**... screenshot of relevant dialog**

[Read more about projects...](Projects)

## LCI databases
After adding the default data, you can create or import a database with the `New` and `Import Database` buttons. 

**... Screenshot of AB left pane until new/import buttons**

### New databases
With `New` you can create a completely empty database with any given name and
enter your own activity data.

[Read more about activities...](Activities)

### Importing databases
Clicking 'Import' will open a new dialog that will allow you to select how you want to import data into brightway 
(and by extension, the Activity Browser).
There are two main options: 'remote data' and 'local data':

<details><summary><b>Remote database import</b></summary>

We currently support 2 remote databases, Ecoinvent and Forwast:

#### Importing Ecoinvent
[**Ecoinvent**](https://ecoinvent.org/) is a paid database you can install directly in Activity Browser if you have a 
valid ecoinvent license and login information.

#### Importing Forwast
[**Forwast**](http://forwast.brgm.fr/) is a free database you can install directly in Activity Browser.
</details>

<details><summary><b>Local database import</b></summary>

We support various local import methods
- Local 7z-archive of ecospold2 files
- Local directory of ecospold2 files
- Local Excel file
- Local Brightway database file
</details>

[Read more about databases...](Databases)

## Running an LCA calculation
To run an LCA, you must first create a calculation setup, add at least one reference flow and one impact category 
to be able to calculate results.

[Read more about LCA calculation setups...](LCA-Calculation_Setups)

[Read more about LCA results...](LCA-Results)

[Follow a tutorial to do your first LCA...](Tutorials#your-first-lca)

# Additional Resources
- [Youtube tutorials](https://www.youtube.com/channel/UCsyySKrzEMsRFsWW1Oz-6aA/)
- [Introduction video by ETH Zurich](https://www.youtube.com/watch?v=j3uLptvsxeA)
- [AB Discussions page](https://github.com/LCA-ActivityBrowser/activity-browser/discussions)
- [AB scientific article](https://doi.org/10.1016/j.simpa.2019.100012)
- The AB has two mailing lists, for [updates](https://brightway.groups.io/g/AB-updates) and [user exchange](https://brightway.groups.io/g/AB-discussion)
- [Brightway2](https://brightway.dev/)
- [Global Sensitiviy Analysis paper](https://onlinelibrary.wiley.com/doi/10.1111/jiec.13194) describing GSA as implemented in the AB; see also our [wiki](https://github.com/LCA-ActivityBrowser/activity-browser/wiki/Global-Sensitivity-Analysis)
- [Modular LCA paper](https://link.springer.com/article/10.1007/s11367-015-1015-3); [documentation modular LCA](http://activity-browser.readthedocs.io/en/latest/index.html); re-implementation of modular LCA into the AB is [ongoing](https://github.com/marc-vdm/activity-browser/tree/mLCA)

# Need help?
Activity Browser supports its users through the community.
If you have **questions** about using Activity Browser and can't find the answer in this wiki, ask it on our 
[discussions](https://github.com/LCA-ActivityBrowser/activity-browser/discussions) page! 
If you have **found a problem** or have **suggestions to improve** Activity Browser, open an 
[issue](https://github.com/LCA-ActivityBrowser/activity-browser/issues).
If you want to **contribute to the Activity Browser** project, you can check out our 
[contributing](https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/CONTRIBUTING.md)
page to see how you can help out.
