---
title: Database Products
parent: Panes
---

<div class="image-container">
<div>
    <h1 class="fs-9">Database Products pane</h1>
    <p class="fs-6 fw-300">The Database Products pane shows what nodes are in the currently selected database.</p>
</div>
<img src="../../assets/panes-database-products.png" width="250"/>
</div>

## Elements
### Quick Search
A search bar at the top of the pane allows you to quickly filter and find specific database products by typing keywords. 
You can also build complex queries by using an equal sign (`=`) before a Pandas query syntax.

#### Query Search
You can search for exact items by writing queries using the 
[pandas query language](https://pandas.pydata.org/docs/dev/reference/api/pandas.DataFrame.query.html).
To do this, you must start your search with `=` and then write the query.
If the query is incorrect, the search bar will turn red and no search is done.

> [!TIP]
> A [pandas query](https://pandas.pydata.org/docs/dev/reference/api/pandas.DataFrame.query.html)
> makes use of logical operations like:
> - `==` equals
> - `!=` does not equal 
> - `~` NOT
> - `&` AND
> - `|` OR
> - `(` and `)` to chain logical operations
> 
> You can also make use of other pandas operations to check for data like:
> - `column.str` to ensure all content of that column is interpreted as text
> - `column.str.contains()` to search within text (use `.contains("text", False)` for case in-sensitive)
> - `column.isin()` to check if values are in a list of items

Below are some examples of queries, getting progressively more complex:

| Query                                                                 | Description                                                                                                  |
|-----------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| `=product=="apple"`                                                   | Find all rows where column `product` is (`==`) **Exactly** `apple`                                           |
| `=product!="apple"`                                                   | Find all rows where column `product` is (`!=`) **not** `apple`                                               |  
| `=product.str.contains("apple")`                                      | Find all rows where column `product` contains `apple`                                                        |
| `=~product.str.contains("apple")`                                     | Find all rows where column `product` does not (`~`) contain `apple`                                          |
| `=product.isin(["apple", "pear"])`                                    | Find all rows where column `product` matches **Exactly** an item in `["apple", "pear"]`                      |
| `=(product.str.contains("apple") \| product.str.contains("pear"))`    | Find all rows where column `product` contains `apple` OR (`\|`) `pear`                                       |
| `=(product.str.contains("apple") & ~activity.str.contains("market"))` | Find all rows where column `product` contains `apple` AND (`&`) column `activity` does not contain `market`  |

### Products View
The Products view displays a list of all the products in the currently selected database, along with some key attributes like: type, unit, and location. If the database is based on the [Functional SQLite backend](../../advanced-topics/multifunctional-databases), only products are shown, grouped by their processors.

## Actions
### Open Process
Open a process in the Process Page by double-clicking the entry, or by right-clicking and selecting "Open process". This will open the Process Details Page, where you can view and edit the process details.

### New Process
Right-click in the Products view and select "New process" to create a new process in the currently selected database. You will be prompted to enter a name, product name, unit, and location for the new process, after which it will be created and opened in the Process Details Page.

### Duplicate Process
Right-click a process and click the "Duplicate process" button to create a copy of the selected process. After duplicating the process and its products, it will be opened in the Process Details Page.

### Delete Process
Right-click a process and click the "Delete process" button to remove it **and its products** from your project. You will be prompted to confirm the deletion. This action cannot be undone.

### Delete Product
Right-click a product and click the "Delete product" button to remove it from your project. You will be prompted to confirm the deletion. This action cannot be undone. This will not delete the process, only the selected product.

### Create Setup
Right-click a product and click the "Create setup" button to create a new calculation setup with the selected product as the functional unit. You will be prompted to enter a name for the new calculation setup, after which it will be created and opened in the Calculation Setup Page.

### SDF to Clipboard
Right-click a product and click the "SDF to clipboard" button to copy the product's SDF (Scenario Difference File) representation to your clipboard. This is useful for manually creating SDF's for [scenario calculations](../../advanced-topics/scenario-calculations.md).
