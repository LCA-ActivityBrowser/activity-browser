---
title: Creating databases
parent: Getting started
nav_order: 3
---
# Creating LCI Databases
{: .fs-9 }

Databases store the processes, products and biosphere flows of your project.
{: .fs-6 .fw-300 }

Databases are a core component of Brightway and Activity Browser. They store the life cycle inventory (LCI), and elementary flow data, which is essential for conducting life cycle assessments (LCA). In this section, we will guide you through the process of creating and managing LCI databases in Activity Browser. 

## Background databases
Although not strictly necessary, most projects will rely on some sort of background database, or at least a database with elementary flows. Background databases provide the necessary data for modeling the life cycle of products and services, including information on raw materials, energy use, emissions, and waste generation.

If you are using a Brightway template project, it will come pre-loaded with an elementary flow database (e.g. **biosphere3**). If you are starting from an empty project, you will need to import or create one before you can start effectively modeling your own processes.

### Background data from ecoinvent
If you have access to the ecoinvent database, you can import it into your project using the Activity Browser. To do this, open the **Project** menu in the top left corner of the application window and select **Import database > ecoinvent...** This will open a wizard to guide you through importing the ecoinvent database, biosphere and impact categories.

## Foreground databases
Foreground databases contain the processes and products that you create and modify yourself. You can create multiple foreground databases within a single project to help organize your work in a meaningful way. For example, you might have one database for a specific product system and another for a different product system.

### Creating a new foreground database
To create a new foreground database, open the **Project** menu in the top left corner of the application window and select **New database...** You will be prompted to enter a name for your new database. Choose a descriptive name that will help you identify the database later. After entering the name, click **Ok**. The new database will be created and opened in the Activity Browser so you can start adding processes and products.

### Importing and exporting databases
You can also import and export databases in Activity Browser. This is useful if you want to share your databases with others or if you want to back up your work. Activity Browser supports importing and exporting databases in several formats, including Brightway's `.bw2data` format and `.xlsx`.

To import a database, open the **Project** menu in the top left corner of the application window and select **Import database** You will be prompted to select the file containing the database you want to import. After selecting the file, click **Ok**. The database will be imported and opened in the Activity Browser.
