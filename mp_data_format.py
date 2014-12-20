"""

Data exchange format for Process Subsystems
It can be used to:
- store and load PSS from file
- as keyword arguments to initialize a ProcessSubsystem object

All other information, such as scaling of edges, LCA results, etc.
can be retrieved from the ProcessSubsystem objects methods.

"""

pss_data_format = [
    {
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
        # OPTIONAL
        # Normally output based scaling (True). For multi-output activities this can be set to False.
        # In that case the scaling activities are always scaled with 1.0. Product outputs need to be adapted manually.
        # This allows to model multiple outputs that do not add up to 1 (e.g. 0.46 MJ heat and 0.08 kWh electricity).
        'output_based_scaling': True,
        # 'edges': [ # theoretically not necessary, but more convenient and perhaps helpful
        #     (parent_key, child_key),
        # ],
    },
    # ...
]