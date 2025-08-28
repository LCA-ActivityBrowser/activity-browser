---
title: Processing datapackages
parent: Functional SQLite
nav_order: 4
---
# Processing tables into datapackages
{: .fs-9 }

Creating the technosphere and biosphere matrices for LCA calculations.
{: .fs-6 .fw-300 }

In Brightway25 LCI data and impact categories are processed into so-called "datapackages". A datapackage is a collection of matrices and metadata that can be used for LCA calculations. The datapackage is created from the data stored in the backend in the `processing` step.

The `FunctionalSqliteBackend` extends the default processing step to deal with multifunctional processes. It is during processing that the edges going into and out of multifunctional processes are allocated to the different products of the process. 

This is done using the `allocation_factor` property of each product, which defines the share of the process inputs and emissions that are allocated to this product. See the [documentation on allocation](allocation) for more information on how to set allocation factors.

## Joining product edges to processes
For merging product edges to processes, we collect all `biosphere` and `technosphere` edges and join their output key to the `processor` key of the products. This creates a new virtual edge (i.e. not stored in the database) for each product of the process. The amount of the new edge is calculated by multiplying the original edge amount by the `allocation_factor` of the joined product. The virtual edges are then used to create the technosphere and biosphere matrices.

### Small example
Imagine two products produced by the same process:

| Name | Key               | Processor | Allocation factor |
|:------|:------------------|:----------|:------------------|
| Product A | `(my_db, prod_a)` | `(my_db, proc_1)` | `0.7` |
| Product B | `(my_db, prod_b)` | `(my_db, proc_1)` | `0.3` |

And a technosphere edge going into the process:

| Input                 | Output                                          | Type          | Amount   |
|:----------------------|:------------------------------------------------|:--------------|:---------|
| `(other_db, input_1)` | `(my_db, proc_1)`                              | `technosphere` | `100`    |

When processing this database the backend will join the product table to the edge table on the output of the edge and the processor of the product. This will create two new edges, one for each product. The amount of each new edge is calculated by multiplying the original edge amount by the `allocation_factor` of the product. This results in the following virtual edges, that are then used to create the technosphere matrix:

| Input                 | Output                                          | Type          | Amount   | 
|:----------------------|:------------------------------------------------|:--------------|:---------|
| `(other_db, input_1)` | `(my_db, prod_a)`                              | `technosphere` | `70`     |
| `(other_db, input_1)` | `(my_db, prod_b)`                              | `technosphere` | `30`     |


