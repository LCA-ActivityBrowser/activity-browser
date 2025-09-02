---
title: Data structure
parent: Functional SQLite
nav_order: 1
---
# Data structure of Functional SQLite
{: .fs-9 }

How this backend stores processes and products
{: .fs-6 .fw-300 }

In the classic Brightway `SQLiteBackend`, all nodes are stored as `Activity` objects. In the Functional SQLite backend, we differentiate between `Process` and `Product` objects. Both are extensions of the `Activity` class, but they have different properties, methods and constraints.

## Processes
Processes represent the actual production activities. 

#### Type
Each process can have multiple products, depending on how many products a process has, the process can be of type `process` (one product), `multifunctional` (more than one product) or `nonfunctional` (no products).

#### Allocation
Processes can also have an 'allocation' property, which defines how allocation factors for the products of the process are calculated. Default is `equal`, which means that all products get the same allocation factor. You can also choose to allocate by a specific product property (e.g. mass, price) or set allocation factors manually. Read more about allocation in the [allocation documentation](allocation).

## Products
Products represent the outputs of a process. 

#### Processor
Each product belongs to exactly one process: the so-called `processor`. The `processor` is defined in two ways: through the `processor` attribute of the product, and through the `production` edge going from the product to the process. `bw-functional` checks that both definitions are consistent when saving a product in which the `processor` attribute is leading.

#### Type
Depending on whether the production edge is positive or negative a product can be of type `product` (positive production) or `waste` (negative production). If there is no production edge or the processor is not found, the product is of type `orphaned_product`, although this should not happen.

#### Properties
Products can have additional properties defined in the `properties` attribute. These properties can be used for [allocation](allocation) of process edges to products. Read more about defining product properties in the [product properties documentation](product-properties).

#### Allocation_factor
Products also have an `allocation_factor` attribute, which defines the share of the process inputs and emissions that are allocated to this product. This value needs to be set for each product of a multifunctional process. Read more about calculating allocation factors in the [allocation documentation](allocation).

## Example database
Here is an example of the data structure in which processes and products are stored in the Functional SQLite backend:

```python
{
    ('example', 'proc_1'): {
        'id': 219057417899814912,  
        'database': 'example',
        'code': 'proc_1',
        'name': 'Process 1',
        'type': 'multifunctional',  # Two products, so multifunctional
     
        'location': 'GLO',
        
        # Process specific properties
        'allocation': 'mass',  # Allocate by the 'mass' property of the products
        
        # Two products defined through production exchanges
        'exchanges': [
            {'input': ('example', 'prod_a'),
             'output': ('example', 'proc_1'), 'amount': 1.0, 'type': 'production'},
            {'input': ('example', 'prod_b'),
             'output': ('example', 'proc_1'), 'amount': 1.0, 'type': 'production'}
        ]
    },
    ('example', 'prod_a'): {
        'id': 219057418856116224,
        'database': 'example',
        'code': 'prod_a',
        'name': 'Product A',
        'type': 'product',
        
        'location': 'GLO',
        'unit': 'unit',
        
        # Product specific properties
        'processor': ('example', 'proc_1'),  # The processor is defined through this attribute
        'properties': {'mass': {'unit': 'kg', 'normalize': True, 'amount': 1.0}},  # This product has a mass of 1 kg per amount
        'allocation_factor': 0.25,  # The allocation factor is calculated based on the mass property of both products
        
        'exchanges': []  # Products do not have exchanges, they are defined through their processor
    },
    ('example', 'prod_b'): {
        'id': 219057483192545280,
        'database': 'example',
        'code': 'prod_b', 
        'name': 'Product B',
        'type': 'product',
        
        'location': 'GLO',
        'unit': 'unit', 
       
        # Product specific properties
        'processor': ('example', 'proc_1'),   # The processor is defined through this attribute
        'properties': {'mass': {'unit': 'kg', 'amount': 3.0, 'normalize': True}},  # This product has a mass of 3 kg per amount
        'allocation_factor': 0.75,  # The allocation factor is calculated based on the mass property of both products
        
        'exchanges': []  # Products do not have exchanges, they are defined through their processor
    }
}
```