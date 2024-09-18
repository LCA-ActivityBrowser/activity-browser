> [!IMPORTANT]
> This wiki section is __incomplete__ or __outdated__.
> 
> Please help us improve the wiki by reading our
> [contributing guidelines](https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/CONTRIBUTING.md#wiki).

Databases are the main way in which Brightway manages and stores [Activities](Activities). Use databases to organize
your data in a meaningful way, for example by separating foreground and background systems. 

Brightway databases consist of two parts: 

1. **Backend:** this is where the actual activity data lives. Most users will be using the SQLite backend, which stores 
data in the _databases.db_ found in the project folder.
2. **Metadata:** this is where database specific metadata is stored, such as dependent databases, number of activities,
and time of last edit.

Databases that are installed in a project may be found in the `Databases` section, part of the `Project` panel. This 
section shows a table that displays a selection of the metadata for all the databases in the project. **Note:** this
panel is not yet visible when no databases have been installed into the project yet. Instead, a button to set up your
project will be shown.

## Opening a database
You can open a database by double-clicking its entry within the `Databases` section. This will open a tab at the bottom
of the `Project` panel that contains a table showing all [activities](Activities) that the database contains.

## Creating a new database
You can create a new database by clicking the `New database...` button in the `Databases` section. This will prompt you
to enter a unique name for the database, after which the newly created database will open and you can start adding
activities as desired.

## Deleting a database
You can delete a database by right-clicking on its entry withing the `Databases` section and selecting `Delete database` This will prompt you for a
confirmation. Note that any exchanges that are dependent on activities within the database will be removed as well. Make
sure you anticipate this.

## Duplicating a database
You can duplicate a database by right-clicking on its entry withing the `Databases` section. This will prompt to enter a 
unique name for the database, after which the newly duplicated database will open.

