from typing import Literal, Optional
from loguru import logger
from threading import RLock

import pandas as pd

from .fields import all_fields, all_types


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

        logger.debug(f"Initializing MetaDataStore: {id(self)}")

        if self._initialized:
            return
        self._initialized = True

        self._dataframe = pd.DataFrame()
        self._df_lock = RLock()

        self._added: set[tuple[str, str]] = set()
        self._updated: set[tuple[str, str]] = set()
        self._deleted: set[tuple[str, str]] = set()

        self.loader = MDSLoader(self)
        self.updater = MDSUpdater(self)
        self.searcher: MDSSearcher | None = None  # initialized by the loader

    @property
    def dataframe(self) -> pd.DataFrame:
        with self._df_lock:
            copy = self._dataframe.copy()
        return copy

    @dataframe.setter
    def dataframe(self, df: pd.DataFrame) -> None:
        # Ensure all expected columns are present, in the correct order, and with the correct types
        df = df.reindex(columns=all_fields)[all_fields].astype(all_types)

        # No NaN values in object columns, use None instead
        for col, col_type in all_types.items():
            if col_type != object:
                continue
            df[col] = df[col].where(df[col].notnull(), None)

        # Set the internal dataframe
        with self._df_lock:
            self._dataframe = df

    @property
    def databases(self):
        with self._df_lock:
            databases = set(self._dataframe.index.get_level_values(0).unique().tolist())
        return databases

    @property
    def keys(self):
        with self._df_lock:
            keys = set(self._dataframe.index.tolist())
        return keys

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

    def flush_mutations(self) -> tuple[set[tuple[str, str]], set[tuple[str, str]], set[tuple[str, str]]]:
        from activity_browser.bwutils import filesystem

        if not (self._added or self._updated or self._deleted):
            return set(), set(), set()

        added = self._added.copy()
        updated = self._updated.copy()
        deleted = self._deleted.copy()

        self._added.clear()
        self._updated.clear()
        self._deleted.clear()

        cache_path = filesystem.get_project_ab_path() / "metadatastore_cache.pkl"
        with self._df_lock:
            self._dataframe.to_pickle(cache_path)

        return added, updated, deleted

    def match(self, **kwargs: dict[str, str]) -> pd.DataFrame:
        """Return a slice of the dataframe matching the criteria.
        """
        with self._df_lock:
            df = self._dataframe.query(
                " and ".join(
                    [
                        f"`{key}`.astype('str') == {str(value)!r}" if not pd.isna(value) else f"`{key}`.isnull()"
                        for key, value in kwargs.items()
                    ])
            ).copy()

        return df

    def get_metadata(self, keys: list = None, columns: list = None) -> pd.DataFrame:
        """Return a slice of the dataframe matching row and column identifiers.

        NOTE: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#deprecate-loc-reindex-listlike
        From pandas version 1.0 and onwards, attempting to select a column
        with all NaN values will fail with a KeyError.
        """
        keys = keys if keys is not None else self._dataframe.index.tolist()
        columns = columns if columns is not None else all_fields

        with self._df_lock:
            df = self._dataframe.loc[pd.IndexSlice[keys], :].copy()
        return df.reindex(columns, axis="columns")

    def get_database_metadata(self, db_name: str, columns: list = None) -> pd.DataFrame:
        columns = columns if columns is not None else all_fields

        if db_name not in self.databases:
            return pd.DataFrame(columns=columns or all_fields)

        with self._df_lock:
            df = self._dataframe.loc[[db_name], columns].copy()
        return df.reindex(columns, axis="columns")

    def search(self, query: str, columns: list = None) -> pd.DataFrame:
        if not self.searcher:
            logger.warning(f"Attempted to search metadata before searcher was initialized.")
            return pd.DataFrame(columns=columns or all_fields)

        params, query = get_query_parameters(query)
        result = self.searcher.search(query)
        return self._meta_from_result(params, result, columns)

    def search_database(self, query: str, database: str, columns: list = None) -> pd.DataFrame:
        if not self.searcher:
            logger.warning(f"Attempted to search metadata before searcher was initialized.")
            return pd.DataFrame(columns=columns or all_fields)

        params, query = get_query_parameters(query)
        result = self.searcher.fuzzy_search(query, database=database)
        return self._meta_from_result(params, result, columns)

    def _meta_from_result(self, params: dict, result: list[int], columns: list = None) -> pd.DataFrame:
        with self._df_lock:
            df = self._dataframe.loc[self.dataframe["id"].isin(result), columns or all_fields]
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
            df = df.copy()

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
