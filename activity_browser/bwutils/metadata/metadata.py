from time import time
from loguru import logger
from typing import Literal

import pandas as pd

from .fields import all, all_types


class MetaDataStore():
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        from .loader import MDSLoader
        from .updater import MDSUpdater

        if self._initialized:
            return

        self._dataframe = pd.DataFrame()

        self._added: set[tuple[str, str]] = set()
        self._updated: set[tuple[str, str]] = set()
        self._deleted: set[tuple[str, str]] = set()

        self.loader = MDSLoader(self)
        self.updater = MDSUpdater(self)

        self._initialized = True

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._dataframe

    @dataframe.setter
    def dataframe(self, df: pd.DataFrame) -> None:
        # Ensure all expected columns are present, in the correct order, and with the correct types
        df = df.reindex(columns=all)[all].astype(all_types)

        # Set the internal dataframe
        self._dataframe = df

    @property
    def databases(self):
        return set(self.dataframe.get("database", []))

    def register_mutation(self, key: tuple[str, str], action: Literal["add", "update", "delete"]):
        if action == "add":
            self._added.add(key)
            self._updated.discard(key)
            self._deleted.discard(key)

        elif action == "update":
            if key not in self._added:
                self._updated.add(key)

        elif action == "delete":
            if key in self._added:
                self._added.discard(key)
            else:
                self._deleted.add(key)
            self._updated.discard(key)
        else:
            raise ValueError(f"Unknown action: {action}")

    def match(self, **kwargs: dict[str, str]) -> pd.DataFrame:
        """Return a slice of the dataframe matching the criteria.
        """
        df = self.dataframe.query(
            " and ".join(
                [
                    f"`{key}` == '{value}'" if not pd.isna(value) else f"`{key}`.isnull()"
                    for key, value in kwargs.items()
                ])
        )

        return df

    def get_metadata(self, keys: list, columns: list) -> pd.DataFrame:
        """Return a slice of the dataframe matching row and column identifiers.

        NOTE: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#deprecate-loc-reindex-listlike
        From pandas version 1.0 and onwards, attempting to select a column
        with all NaN values will fail with a KeyError.
        """
        df = self.dataframe.loc[pd.IndexSlice[keys], :]
        return df.reindex(columns, axis="columns")

    def get_database_metadata(self, db_name: str, columns: list = None) -> pd.DataFrame:
        if db_name not in self.databases:
            return pd.DataFrame(columns=all)
        return self.dataframe.loc[[db_name], columns or all]
