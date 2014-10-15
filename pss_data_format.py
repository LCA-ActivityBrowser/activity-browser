pss_data = [
    {
        'name': "custom_name",
        'outputs': [
            (key, 'custom_name', 'custom_amount'),
        ],
        # 'chain': [
        #     (parent_key, child_key),
        # ],
        'edges': [
            (parent_key, child_key, amount),
        ],
        'cuts': [
            (parent_key, child_key, 'custom_name'),
        ],
    }
]