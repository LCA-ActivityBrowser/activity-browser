"""Tests for scenario database relinking during superstructure import."""

import pandas as pd

from activity_browser.bwutils.superstructure import dataframe as ss_df


def _activity_metadata():
    df = pd.DataFrame(
        [{
            "id": 1,
            "code": "act1",
            "database": "local_db",
            "name": "Process A",
            "product": "steel",
            "location": "GLO",
            "categories": None,
            "key": ("local_db", "act1"),
            "type": "process",
            "synonyms": None,
            "unit": "kg",
            "CAS number": None,
            "processor": None,
            "allocation": None,
            "allocation_factor": float("nan"),
            "properties": None,
        }]
    )
    df.index = pd.MultiIndex.from_tuples([("local_db", "act1")], names=["database", "code"])
    return df


def test_scenario_replace_databases_relinks_foreign_name():
    ss_df.metadata._dataframe = _activity_metadata()

    df = pd.DataFrame([{
        "from database": "foreign_db",
        "to database": "local_db",
        "from activity name": "Process A",
        "from categories": float("nan"),
        "from reference product": "steel",
        "from location": "GLO",
        "to activity name": "Other",
        "to categories": float("nan"),
        "to reference product": "other",
        "to location": "GLO",
        "from key": None,
        "to key": ("local_db", "act1"),
        "flow type": "technosphere",
    }])

    result = ss_df.scenario_replace_databases(df.copy(), {"foreign_db": "local_db"})

    assert result.loc[0, "from database"] == "local_db"
    assert result.loc[0, "from key"] == ("local_db", "act1")
