"""

Data format for Meta-Processes
It is used to define and store meta-processes.

All other properties are calculated based on this data,
e.g. scaling of edges, LCA results, etc. using the methods
of the MetaProcess class.

"""

data_format = {
        'name': "custom_name",
        'outputs': [
            (key, 'custom_name', 'custom_amount'),
        ],
        'chain': [
            (parent_key, child_key),
        ],
        'cuts': [
            (parent_key, child_key, 'custom_name', amount),
        ],
        'output_based_scaling': True,  # optional, by default True
        # If False, the scaling activity will be set to 1.0 independently of the outputs.
        # This can be useful for multi-output activities, if
        # a) product outputs are not defined in the dataset (as in brightway2 for ecoinvent multi-output activities).
        # b) if 
        # where product outputs are not imported in brightway2. If set False, scaling activities are scaled with 1.0
        # independently of the product output, which needs to be defined and checked manually.
        # This allows to model multiple outputs that do not add up to 1 (e.g. 0.46 MJ heat and 0.08 kWh electricity).
}