[Learn how to install Activity Browser...](Installation-Guide)

## Starting Activity Browser 3
First activate the environment where the activity browser is installed. This may differ based on the installation method you used. If you installed Activity Browser with conda, you can activate the environment with:

```bash
conda activate ab
```

If you installed Activity Browser in a virtual environment using pip, you can activate it with:

```bash
source /path/to/your/venv/bin/activate
```

Then simply run `activity-browser` and the application will open.

## Understanding Activity Browser terms
Activity Browser uses [Brightway](https://docs.brightway.dev/en/latest/) for its data management and calculations. 
Brightway has its own 'accent' of LCA terms,
you can compare LCA terms from Brightway, [ISO 14044 (2006)](https://www.iso.org/standard/38498.html) and others in the
[Brightway Glossary](https://docs.brightway.dev/en/latest/content/overview/glossary.html).

## Organization of data in Brightway and Activity Browser
Data in Brightway is organized into projects
- Projects contain databases, impact categories, calculation setups and more
  - Databases contain activities (biosphere and technosphere)
    - Activities are the building blocks of your LCA model 
- Impact categories are used to score your LCA models against
- Calculation setups are the combinations of reference flows and impact categories that you can calculate
- Projects also contain other data, such as parameters and plugin settings.

![brightway organizational structure](./assets/brightway_org-scheme.png)
<sup>
_Image copied from the
[Brightway documentation](https://docs.brightway.dev/en/latest/content/theory/structure.html#brightway-objects)._
</sup>

Read more about how data is organized in the 
[Brightway documentation](https://docs.brightway.dev/en/latest/content/theory/structure.html#brightway-objects).

## User interface
Activity Browser 3 is organized into `Panes` and `Pages`. `Panes` are the draggable windows that you can move around, and stack on top of each other (e.g. `Databases`, `Impact Categories`, `Calculation Setups`). `Pages` are central to the application and show specific content (e.g. `Activity Details`, `Parameters`, `LCA Results`).


### Panes
The [`Databases`](Databases) pane shows the databases currently loaded into your project.
The [`Impact Categories`](Impact-Categories) pane shows all impact categories that are installed in the current project.
The [`Calculation Setups`](LCA-Calculation-Setups) pane allows you to open, create and delete new calculation setups.

### Pages
The [`Parameters`](Parameters) page allows you to manage your parameters.
The [`LCA Setup`](LCA-Results) page allows you to create and manage your LCA calculation setups.
The [`LCA Results`](LCA-Results) page shows the results of the calculations you do.

## Setting up a project
When creating a new project you must first decide whether you want to create a project totally from scratch, or whether you want to set up a project from a Brightway template. Brightway templates are pre-configured projects that contain a biosphere database and impact categories. It is the recommended way to start a new project if you do not have e.g. an ecoinvent license to install the ecoinvent database, biosphere and impact categories.

You can create a new project from a template by navigating to the `Project` menu, selecting the `New Project` submenu, and then selecting your desired template from the `From template` submenu.

If you want to create a project from scratch, you can select the `New Project` option in the `Project` menu. This will create a new project with no data, and you can then add databases, impact categories and calculation setups as needed.

[Read more about projects...](Projects)

## Databases
You can add databases to your project in two ways: by creating a new database, or by importing an existing database.
[Read more about databases...](Databases)

### New databases
By clicking the `New database` button in either the `Project` menu or the context menu of the `Databases` pane, you can create a new database. This will open a dialog where you can enter the name of the new database and select the back-end of the database.

You can choose between the following back-ends:
- **sqlite** The standard back-end for Brightway databases.
- **functional-sqlite** An experimental backend that allows for multifunctional processes.

[Read more about activities...](Activities)

### Importing databases
Clicking 'Import' will open a new dialog that will allow you to select how you want to import data into brightway (and by extension, the Activity Browser).
There are three options: `.bw2package`, `.xlsx`and `ecoinvent`:

- **.bw2package**: This is the standard format for Brightway databases. You can import a `.bw2package` file by selecting the option in the import menu.
- **.xlsx**: This is a spreadsheet format that can be used to import data into Brightway. You can import an `.xlsx` file by selecting the option in the import menu.
- **ecoinvent**: If you have an ecoinvent license, you can import the ecoinvent database by selecting the `ecoinvent` option in the dialog. This will open a new dialog where you can login with your credentials and select the version of ecoinvent you want to import.

## Running an LCA calculation
To run an LCA, you must first create a calculation setup, add at least one reference flow and one impact category to be able to calculate results. You can do this by navigating to the `Calculation Setups` pane, clicking the `New Calculation Setup` button, and then adding reference flows and impact categories to the setup by dragging them into the page from the appropriate panes.

## Additional Resources
- [Youtube tutorials](https://www.youtube.com/channel/UCsyySKrzEMsRFsWW1Oz-6aA/)
- [Introduction video by ETH Zurich](https://www.youtube.com/watch?v=j3uLptvsxeA)
- [AB Discussions page](https://github.com/LCA-ActivityBrowser/activity-browser/discussions)
- [AB scientific article](https://doi.org/10.1016/j.simpa.2019.100012)
- The AB has two mailing lists, for [updates](https://brightway.groups.io/g/AB-updates) and [user exchange](https://brightway.groups.io/g/AB-discussion)
- [Brightway2](https://brightway.dev/)
- [Global Sensitiviy Analysis paper](https://onlinelibrary.wiley.com/doi/10.1111/jiec.13194) describing GSA as implemented in the AB; see also our [wiki](https://github.com/LCA-ActivityBrowser/activity-browser/wiki/Global-Sensitivity-Analysis)
- [Modular LCA paper](https://link.springer.com/article/10.1007/s11367-015-1015-3); [documentation modular LCA](http://activity-browser.readthedocs.io/en/latest/index.html)
