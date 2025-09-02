---
title: Allocation
parent: Functional SQLite
nav_order: 3
---
# Allocating burdens to products
{: .fs-9 }

Calculating what share of the process inputs and emissions are allocated to each product.
{: .fs-6 .fw-300 }

In the `FunctionalSqliteBackend`, multifunctional processes use products and elementary flows (defined through `technosphere` and `biosphere` edges) and produce products (defined through `production` edges). In the end to create a square technosphere matrix, we need to allocate the inputs and emissions of the process to its product nodes.

For this `FunctionalSqliteBackend` expects that for each product the `allocation_factor` property is set to a numerical value. This value defines the relative share of the process inputs and emissions (burdens) that are allocated to this product.

## Setting allocation factors
In the Activity Browser 3, there are multiple ways to set allocation factors for products:
- **Equal** burdens are distributed equally among all products.
- **By property** burdens are distributed according to a specific product property (e.g. mass, price).
- **Manually** you can set the allocation factor for each product manually.

You can choose from the available options in the **Allocation** dropdown in the header of the Process details. `allocation_factor` values are automatically updated when you select one of the options.

### Using product properties for allocation
You can only use product properties for allocation if all the products of the process have the same property defined. For example, if you want to allocate by mass, all products need to have a `mass` property defined. If one or more products do not have the property defined, the option will not be available in the dropdown.

Allocation factors are calculated as such:
```python
allocation_factor = property.amount / sum([property.amount for product of process])
```

### Normalized properties
If you defined a product property with the `normalize` option enabled, the property value will be multiplied by the production amount of the product before being used for allocation. This is useful if you want to allocate by a property that is dependent on the production amount, e.g. price or revenue.

```python
allocation_factor = (property.amount * product.amount) / sum([property.amount * product.amount for product of process])
```

Because most properties are defined as being a value per unit of product (e.g. price per kg), properties are normalized by default in `bw-functional`.
