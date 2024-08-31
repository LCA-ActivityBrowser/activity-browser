<!--
Tutorial writing guidelines:
1. Use the template below
2. Make use of Github Markdown formatting for tips, warnings etc
   https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax
3. Make sure the 'before you start' section is correct
   Link to other tutorials for potentially missing knowledge
4. Use a consistent formatting style for interaction items and names 
   - Refer to buttons, labels and other interactive items with `backticks`
   - Things you name in your tutorial (e.g. database name) with _'italic+quotes'_
5. Make use of screenshots/gifs, annotate them if needed
6. Link to relevant documentation sections where possible
7. Link to your new tutorial in other documentation sections where relevant
8. Update the contents section to add your tutorial

Tutorial template:

## Title
### What will you learn
Write in a few sentences what reader will learn (what problem to solve) from following this tutorial. 

### Before you start
> [!IMPORTANT]
> Make sure you have/know the following:
> - [x] [Have a working installation of Activity Browser](Getting_Started.md#installation-guide)
> - [x] [Have a project set up](Getting_Started.md#setting-up-a-project) 
> - [x] ...

### 1. ...

-->

# Contents

- [General](#general)
  - [Your first LCA](#your-first-lca)
- [Managing activities and databases](#managing-activities-and-databases)
- [Uncertainty](#uncertainty)
- [Flow Scenarios](#flow-scenarios)
- [Parameters](#parameters)

# General

## Your first LCA
### What will you learn
With this tutorial, you will learn the general steps to complete an LCA in Activity Browser.

We will create a simple product-system that produces electricity from coal and calculate the climate change 
and water use impact.

### Before you start
> [!IMPORTANT]
> Make sure you have/know the following:
> - [x] [Have a working installation of Activity Browser](Getting_Started.md#installation-guide)
> - [x] [Have a project set up](Getting_Started.md#setting-up-a-project)
> - [x] Know the basics of LCA

### 1. Create a new database
- Create new database with the name _'first lca tutorial'_, confirm. 
  - **... screenshot of new db button marked and name dialog**

### 2. Create the system
#### 2.1 Creating activities
To assess the environmental impact of generating electricity from coal, we need to model the production of 
electricity and coal first.

- Right-click on your new database in the `Databases` table and choose `New activity`.
  - **... screenshot of context menu and dialog** 
- Name your new activity _'electricity production, coal'_, confirm.
  - This opens your new activity in the `Activity Details` tab on the right.
  - **... screenshot of tab**
  - This tab shows all information about an activity.
  - You can also see your new activity in the database now.

> [!TIP]
> You can only edit activities when the database is not set to `Read-only` and the activity is set to `Edit Activity`.
> You can set these in the `Databases` table and in the top left of the 'Activity Details' tab respectively.
> This is done to avoid accidental changes.
> 
> Your changes are saved automatically.
 
- In the `Products` table, change the `Product` name to _'electricity'_ and `Unit` to _'kilowatt hour'_.
  - Optionally set the `Location` to your favourite country.

> [!NOTE]
> Units in Brightway and Activity Browser are 'just' text. 
> Units don't have an inherent meaning or relationships to each other.

#### 2.2 Linking activities
- In the `Databases` table in the `Project` tab on the left, open the database `biosphere3` by double-clicking on it.

> [!NOTE]
> All databases that you have open in a project are shown as tabs underneath the `Databases` table.

- Search for _'carbon dioxide, fossil'_ in the database the category does not matter right now.
- In the `Activity Details` show the (still empty) `Biosphere Flows` table by ticking the box.
- Drag the _'carbon dioxide, fossil'_ biosphere flow to the `Biosphere Flows` table.
- Set the `Amount` to 0.9 kilogram by double-clicking on the `Amount` field and changing the value.

#### 2.3 Finishing your system
Of course, electricity cannot be generated from nothing, so we need to 
add the production of coal as a new activity to the system.

- Create a new activity named _'coal mining'_ with as `Product` name _'coal'_ and as unit _'kilogram'_.
- Again add the _'carbon dioxide, fossil'_ biosphere flow to the activity, set the `Amount` to 0.15 kilogram.
- Now switch back to the `Activity Details` of the process _'electricity production, coal'_.
- From the database _'first lca tutorial'_ add the _'coal mining'_ activity you just created to the 
  `Technosphere Flows` table of the _electricity production_ process.
- Set the `Amount` to 0.4 kilogram

Now, the mining of coal also takes some electricity, so we need to go back to the coal mining process 
and also add electricity as input there

- Open the _'coal mining'_ activity again and add _'electricity production'_ to the process
- Set the `Amount` to 0.01 kilowatt hour.

#### 2.4 Inspecting your system
You have now finished creating a simple product-system for producing electricity from coal.
You may want to inspect if everything in developing your system went correctly.

In addition to the input flows from the technosphere and the biosphere, you can also see the `Downstream Consumers`, 
which are activities that consume the product your process produces.

You can also look at the supply chain network visually with the `Graph Explorer`.
You can open the graph explorer in two ways; 1) by right-clicking on an activity in a database and choosing 
`Open activity in Graph Explorer`, or 2) in the top left of the `Activity Details`, 
by clicking the `Graph Explorer` logo.

### 3 Creating a calculation setup
Now that we created a product-system, we can calculate its environmental impact.

- On the right, open the tab `LCA setup` and click `New`, name your calculation setup _'first calculation setup'_.
- On the left, find your activity _'electricity production'_ in your database 
  and drag it to the `Reference flows` table.
- On the left, open the tab `Impact Categories` and search for _'GWP100'_ and choose one of the impact categories, 
  drag it to the `Impact categories` table.

### 4 Running an LCA calculation
Now you are ready to calculate results.

- Click the `Calculate` button on the top left of the `LCA Setup` tab.
  - When Activity Browser finished the calculation, it will automatically open the `LCA results` tab on the right.
- Congratulations! You have successfully calculated your first LCA.

> [!NOTE]
> The activities you see in there `Reference flows` table are linked to your system, if you change your system, the changes are saved automatically.
> Do keep in mind that you do need to re-calculate your results every time you make changes.

**... tutorial for searching databases** (filtering data, treeview etc)

**... tutorial for interpreting LCA results** (overview, using contribution filters, sankey)

# Managing activities and databases

**... tutorial for relinking databases**

**... tutorial for exchanges**

# Uncertainty

**... tutorial for adding uncertainty**

**... tutorial for monte carlo**

**... tutorial for GSA**

# Flow Scenarios

**... tutorial for creating scenarios**

**... tutorial for running flow scenarios**

# Parameters

**... tutorial for creating parameters**

**... tutorial for running parameter scenarios**
