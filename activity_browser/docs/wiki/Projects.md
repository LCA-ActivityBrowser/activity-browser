Projects are one of the many ways in which [Brightway](https://docs.brightway.dev/en/latest/) helps you structure your data. 
A project is a standalone environment in which you store your 
[LCI databases](Databases), [Impact Categories](Impact-Categories), [Calculation Setups](LCA-Calculation-Setups) and any other data. 
Data that is stored in project _One_ cannot be used in project _Two_ and vice versa. 
Use this to your advantage in any way you like.

[Read more about data organization in Brightway...](Getting-Started#organization-of-data-in-brightway-and-activity-browser)

Projects are stored separately from your Activity Browser installation in a folder dependent on your operating system
and user preferences. 
This means you can install multiple version of Activity Browser and access the same projects. 
It also means that removing Activity Browser is not going to remove projects or fix any issues related to your project.

If you want to know where a particular project is stored, check the Activity Browser console window, which will display 
the folder for the current project when you open it.

## Selecting a project
When you launch the Activity Browser you will be dropped into your startup project, Brightway's "default" project by
default. 
You can always see what project you are in by checking the window title bar, the toolbar at the bottom of the
screen, or see what project is selected in the drop-down menu at the top of the `Project` tab.

You can switch between projects in one of two ways: through the `Project` > `Open project` menu in the main menu bar 
or you can either choose a project from `Project` tab's drop-down menu.

## Creating a new project
You can create a new project by either `Project` > `New` menu in the main menu bar 
or by clicking the `New` button at the top of the `Project` tab.

You'll be asked to provide a unique name for your new project, after which the Activity Browser will create and switch \
to your new project and allow you to set-up your project in any way you like.

[Read more about setting up a project...](Getting-Started#setting-up-a-project)

## Deleting a project
You can delete your current project by either the
`Project` > `Delete` menu in the main menu bar or by clicking the `Delete` button at the top of the `Project` tab.

You will be asked for confirmation and whether you want to delete the project folder from the disk as well. 
If you do not delete your project from disk, Brightway will just unregister the project, which will hide it from the project selection
menus, but the data is preserved in the project folder mentioned above.
If you choose to delete it from disk entirely, the project and its data are removed entirely.

> [!WARNING]
> Deleting a project from disk can not be undone.
> 
> Make sure you anticipate the consequences of deleting a projecgt before doing so!

## Duplicating a project
You can duplicate your current project by either the `Project` > `Duplicate` menu in the main menu bar 
or clicking the `Duplicate` button at the top of the Project tab.

You will be asked to provide a unique name for your duplicate project, after which the Activity Browser will switch 
to the duplicated project. 
This feature is useful if you want to test out anything that may break your data, by first duplicating your project
you ensure that your data is preserved if you want to return to it.

## Exporting a project
You can export your entire project to a `.tar.gz` archive file. 
This archive will contain all data stored within the project like
[LCI databases](Databases), [Impact Categories](Impact-Categories), [Calculation Setups](LCA-Calculation-Setups) and any other data. 
You can export your project through the `Project` > `Export this project` menu in the
main menu bar.

You will be asked for a location the `.tar.gz` archive with your project data should be saved to. 

> [!NOTE]
> Exporting may take a while to complete, especially for large projects with many databases.

## Importing a project
Similarly, you can also import a project that has been exported to a `.tar.gz` archive. 
You can import the project through the `Project` > `Import a project` menu in the main menu bar.

You will be prompted for a unique project name, after which the project will be installed and the Activity Browser will
switch to your imported project.

## Brightway25 projects
> [!IMPORTANT]
> Brightway25 is not yet officially supported by the Activity Browser. 
> Projects created using Brightway25 use a different structure 
> and managing them through the Activity Browser may cause breaking issues. 
> Brightway25 projects are shown in the project selection menus, but cannot yet be used in Activity Browser. 

If you know what you're doing feel free to enable these projects by setting the `AB_BW25` environmental variable. 
Needless to say this is at your own risk, we will not provide you with support for this yet.
