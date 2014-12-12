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
        # scaling activities: mainly necessary for multi-output activities, where outputs shall be overriden
        # or where artificual outputs shall be added and not used for scaling
        'scaling activities': [
            (key, 'custom_amount')
        ],
        # 'edges': [ # theoretically not necessary, but more convenient and perhaps helpful
        #     (parent_key, child_key),
        # ],
    },
    # ...
]