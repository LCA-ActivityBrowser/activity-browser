> [!IMPORTANT]
> This wiki section is __incomplete__ or __outdated__.
> 
> Please help us improve the wiki by reading our
> [contributing guidelines](https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/CONTRIBUTING.md#wiki).

Databases are the main way in which Brightway manages and stores [Activities](Activities). 
Use databases to organize your data in a meaningful way, for example by separating foreground and background systems. 

[Read more about data organization in Brightway...](Getting-Started#organization-of-data-in-brightway-and-activity-browser)

Brightway databases consist of two parts: 

1. **Backend:** this is where the actual activity data lives. 
   Activity Browser 3 supports two backends for databases: `sqlite` and `functional-sqlite`. 

[//]: # ([You can read more about their differences here.]&#40;Backends&#41;)
2. **Metadata:** this is where database specific metadata is stored, such as dependent databases, number of activities,
   and time of last edit.

Databases that are installed in a project may be found in the `Databases` pane.
This section shows a table that displays a selection of the metadata for all the databases in the project.

## Basic functions

### Opening a database
You can open a database by double-clicking its entry within the `Databases` table. This will open a pane showing all [activities](Activities) that the database contains.

### Creating a new database
You can create a new database by clicking the `New database...` button in the `Databases` pane contextmenu. This will prompt you to enter a unique name for the database, after which the newly created database will open and you can start adding activities as desired.

### Deleting a database
You can delete a database by right-clicking on its entry withing the `Databases` table and selecting `Delete database`, 
this will prompt you for a confirmation. 

> [!WARNING]
> Deleting a database can not be undone and any exchanges between activities in the database and any other database will 
> be deleted, all activities in the database that were used in a calculation setup will also be removed from the setup. 
> 
> Make sure you anticipate the consequences of deleting a database before doing so!

### Duplicating a database
You can duplicate a database by right-clicking on its entry withing the `Databases` table. 
This will prompt to enter a unique name for the new database, after which the newly duplicated database will open.


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

