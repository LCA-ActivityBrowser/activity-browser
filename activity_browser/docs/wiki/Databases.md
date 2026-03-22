> [!IMPORTANT]
> This wiki section is __incomplete__ or __outdated__.
> 
> Please help us improve the wiki by reading our
> [contributing guidelines](https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/CONTRIBUTING.md#wiki).

DatabasesPane are the main way in which Brightway manages and stores [Activities](Activities). 
Use databases to organize your data in a meaningful way, for example by separating foreground and background systems. 

[Read more about data organization in Brightway...](Getting-Started#organization-of-data-in-brightway-and-activity-browser)

Brightway databases consist of two parts: 

1. **Backend:** this is where the actual activity data lives. 
   Most users will be using the SQLite backend, which stores data in the _databases.db_ found in the project folder.
2. **Metadata:** this is where database specific metadata is stored, such as dependent databases, number of activities,
   and time of last edit.

DatabasesPane that are installed in a project may be found in the `DatabasesPane` section, part of the `Project` panel. 
This section shows a table that displays a selection of the metadata for all the databases in the project. 

> [!NOTE]
> This panel is not yet visible when no databases have been installed into the project yet. 
> Instead, a button to set up your project will be shown.
> 
> [Read more about setting up a project...](Getting-Started#setting-up-a-project)

## Basic functions

### Opening a database
You can open a database by double-clicking its entry within the `DatabasesPane` table. 
This will open a tab at the bottom of the `Project` panel that contains a table showing all [activities](Activities) 
that the database contains.

### Creating a new database
You can create a new database by clicking the `New database...` button in the `DatabasesPane` table. 
This will prompt you to enter a unique name for the database, after which the newly created database will open and you 
can start adding activities as desired.

### Deleting a database
You can delete a database by right-clicking on its entry withing the `DatabasesPane` table and selecting `Delete database`, 
this will prompt you for a confirmation. 

> [!WARNING]
> Deleting a database can not be undone and any exchanges between activities in the database and any other database will 
> be deleted, all activities in the database that were used in a calculation setup will also be removed from the setup. 
> 
> Make sure you anticipate the consequences of deleting a database before doing so!

### Duplicating a database
You can duplicate a database by right-clicking on its entry withing the `DatabasesPane` table. 
This will prompt to enter a unique name for the new database, after which the newly duplicated database will open.

### Relinking a database
DatabasesPane are often connected to other databases by exchanges. 
Sometimes, you may want to replace the connections from a database to another, as an example:

You have 2 databases, database _A_ and _B_, _B_ uses activities that are in _A_.
You duplicated a database _A_ to make and test some changes to _A_copy_, and now want to change the links in _B_ to _A_copy_.

To relink a database, you can right-click on its entry in the `DatabasesPane` table and choose `Relink the database`.
In the pop-up, you can choose a new link for every database your database depends on.

Relinking will only work if exact matches are found for the `name`, `reference product` adn `unit` for the activities. 
Any activities not relinked will remain linked to the old database.

> [!NOTE]
> Relinking can be a slow process, as it needs to check every exchange in every activity in the database.

[//]: # (# Importing)

[//]: # (Importing databases is an important aspect of project management. However, there are a myriad of different file formats )

[//]: # (and standards around for LCA data. Activity Browser covers importing for the following formats:)

[//]: # (- Ecospold)

[//]: # (- .bw2data packages)

[//]: # (- Excels in the Brightway2 format)

[//]: # ()
[//]: # ()
[//]: # (## Database import wizard)

[//]: # ()
[//]: # ()
[//]: # (# Exporting)

[//]: # ()
[//]: # (## Database export wizard)

[//]: # ()
[//]: # ()
[//]: # (# Specific tooling)

[//]: # ()
[//]: # (# Database relinking)

