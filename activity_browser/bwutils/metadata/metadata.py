from typing import Literal, Optional
from loguru import logger

import pandas as pd

from .fields import all, all_types


class MetaDataStore:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        from .loader import MDSLoader
        from .updater import MDSUpdater
        from .searcher import MDSSearcher

        if self._initialized:
            return
        self._initialized = True

        self._dataframe = pd.DataFrame()

        self._added: set[tuple[str, str]] = set()
        self._updated: set[tuple[str, str]] = set()
        self._deleted: set[tuple[str, str]] = set()

        self.loader = MDSLoader(self)
        self.updater = MDSUpdater(self)
        self.searcher: MDSSearcher | None = None  # initialized by the loader

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
                    f"`{key}`.astype('str') == {str(value)!r}" if not pd.isna(value) else f"`{key}`.isnull()"
                    for key, value in kwargs.items()
                ])
        )

        return df

    def get_metadata(self, keys: list, columns: list = None) -> pd.DataFrame:
        """Return a slice of the dataframe matching row and column identifiers.

        NOTE: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#deprecate-loc-reindex-listlike
        From pandas version 1.0 and onwards, attempting to select a column
        with all NaN values will fail with a KeyError.
        """
        df = self.dataframe.loc[pd.IndexSlice[keys], :]
        return df.reindex(columns, axis="columns")

    def get_database_metadata(self, db_name: str, columns: list = None) -> pd.DataFrame:
        if db_name not in self.databases:
            return pd.DataFrame(columns=columns or all)
        return self.dataframe.loc[[db_name], columns or all]

    def search(self, query: str, columns: list = None) -> pd.DataFrame:
        if not self.searcher:
            logger.warning(f"Attempted to search metadata before searcher was initialized.")
            return pd.DataFrame(columns=columns or all)

        params, query = get_query_parameters(query)
        result = self.searcher.search(query)
        return self._meta_from_result(params, result, columns)

    def search_database(self, query: str, database: str, columns: list = None) -> pd.DataFrame:
        if not self.searcher:
            logger.warning(f"Attempted to search metadata before searcher was initialized.")
            return pd.DataFrame(columns=columns or all)

        params, query = get_query_parameters(query)
        result = self.searcher.fuzzy_search(query, database=database)
        return self._meta_from_result(params, result, columns)

    def _meta_from_result(self, params: dict, result: list[int], columns: list = None) -> pd.DataFrame:
        df = self.dataframe.loc[self.dataframe["id"].isin(result), columns or all]
        df.sort_values(by="id", inplace=True, key=lambda x: x.map({id_: i for i, id_ in enumerate(result)}))

        extra_query = " & ".join(
            [
                f"`{key}`.astype('str').str.contains('{value}', False)"
                for key, value in params.items()
                if key in df.columns
            ]
        )
        if extra_query:
            df = df.query(extra_query)

        return df

    def auto_complete(self, word: str, context: Optional[set] = None, database: Optional[str] = None):
        if not self.searcher:
            logger.warning(f"Attempted to search metadata before searcher was initialized.")
            return []

        word = self.searcher.clean_text(word)
        completions = self.searcher.auto_complete(word, context=context, database=database)
        return completions

def get_query_parameters(query: str) -> tuple[dict[str, str], str]:
    """Extract key-value pairs from a query string of the form 'key1:value1 key2:value2'."""
    params = {}
    tokens = query.split()
    clean_query = []
    for token in tokens:
        if ':' in token:
            key, value = token.split(':', 1)
            params[key] = value
        else:
            clean_query.append(token)
    return params, ' '.join(clean_query)
