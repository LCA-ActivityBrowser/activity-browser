from typing import Literal, Optional
from loguru import logger

from qtpy.QtCore import QObject

import pandas as pd

from activity_browser.bwutils.settings import Settings
from .fields import all_fields, all_types


def dataframe_for_pickle_cache(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy safe for ``to_pickle`` across pandas versions.

    ``StringDtype`` columns unpickle can raise ``NotImplementedError`` when the
    cache was written with a different pandas build; plain ``object`` strings do not.
    """
    out = df.copy()
    for col in out.columns:
        if isinstance(out[col].dtype, pd.StringDtype):
            out[col] = out[col].astype(object)
    return out


class MetaDataStore(QObject):
    """Singleton class to manage metadata storage, loading, updating, and searching."""
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, parent=None):
        from .loader import MDSLoader
        from .updater import MDSUpdater
        from .searcher import MDSSearcher

        if self._initialized:
            return
        self._initialized = True
        super().__init__(parent=parent)

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
        # Ensure all expected columns are present, in the correct order
        df = df.reindex(columns=all_fields)[all_fields]

        # Apply types carefully - avoid in-place modifications
        for col, col_type in all_types.items():
            if col in df.columns:
                df[col] = df[col].astype(col_type)

        # No NaN values in object columns, use None instead
        for col, col_type in all_types.items():
            if col_type != object or col not in df.columns:
                continue
            df[col] = df[col].where(df[col].notnull(), None)

        self._dataframe = df

    @property
    def databases(self):
        return set(self._dataframe.index.get_level_values(0).unique().tolist())

    @property
    def keys(self):
        return set(self._dataframe.index.tolist())

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

        if Settings()["metadatastore"]["caching_enabled"]:
            cache_path = filesystem.get_project_ab_path() / "metadatastore_cache.pkl"
            dataframe_for_pickle_cache(self._dataframe).to_pickle(cache_path)

        return added, updated, deleted

    def match(self, **kwargs: dict[str, str]) -> pd.DataFrame:
        """Return a slice of the dataframe matching the criteria.
        """
        df = self._dataframe.query(
            " and ".join(
                [
                    f"`{key}`.astype('str') == {str(value)!r}" if not pd.isna(value) else f"`{key}`.isnull()"
                    for key, value in kwargs.items()
                ])
        )

        return df

    def get_metadata(self, keys: list = None, columns: list = None) -> pd.DataFrame:
        """Return a slice of the dataframe matching row and column identifiers.

        NOTE: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#deprecate-loc-reindex-listlike
        From pandas version 1.0 and onwards, attempting to select a column
        with all NaN values will fail with a KeyError.
        """
        keys = keys if keys is not None else self._dataframe.index.tolist()
        columns = columns if columns is not None else all_fields

        df = self._dataframe.loc[pd.IndexSlice[keys], :]
        return df.reindex(columns, axis="columns")

    def get_database_metadata(self, db_name: str, columns: list = None) -> pd.DataFrame:
        columns = columns if columns is not None else all_fields

        if db_name not in self.databases:
            return pd.DataFrame(columns=columns or all_fields)

        df = self._dataframe.loc[[db_name], columns]
        return df.reindex(columns, axis="columns")

    def _pandas_search(self, query: str, database: str = None, columns: list = None) -> pd.DataFrame:
        """Fallback pandas-based search when searcher is not initialized.

        Args:
            query: Search query string, may contain key:value parameters
            database: Optional database name to restrict search
            columns: Optional list of columns to return

        Returns:
            DataFrame with matching results
        """
        params, clean_query = get_query_parameters(query)
        columns = columns if columns is not None else all_fields

        # Start with the full dataframe or database subset
        if database and database in self.databases:
            df = self._dataframe.loc[[database]]
        else:
            df = self._dataframe

        if not clean_query.strip():
            # If no search query, just filter by parameters
            if params:
                extra_query = " & ".join(
                    [
                        f"`{key}`.astype('str').str.contains('{value}', case=False)"
                        for key, value in params.items()
                        if key in df.columns
                    ]
                )
                if extra_query:
                    df = df.query(extra_query)
            return df[columns]

        # Search across text fields: name, product, synonyms, categories, unit, location
        search_fields = ['name', 'product', 'synonyms', 'categories', 'unit', 'location', 'CAS number']
        mask = pd.Series([False] * len(df), index=df.index)

        for field in search_fields:
            if field in df.columns:
                # Case-insensitive search
                mask |= df[field].astype(str).str.contains(clean_query, case=False, na=False)

        df = df[mask]

        # Apply additional parameter filters if any
        if params:
            extra_query = " & ".join(
                [
                    f"`{key}`.astype('str').str.contains('{value}', case=False)"
                    for key, value in params.items()
                    if key in df.columns
                ]
            )
            if extra_query:
                df = df.query(extra_query)

        return df[columns] if columns else df

    def search(self, query: str, columns: list = None) -> pd.DataFrame:
        if self.searcher:
            # Advanced searcher is initialized, so use that
            params, query = get_query_parameters(query)
            result = self.searcher.search(query)
            return self._meta_from_result(params, result, columns)

        # Fallback to simple pandas search
        logger.debug("Using simple pandas search as searcher is not initialized.")
        return self._pandas_search(query, columns=columns)

    def search_database(self, query: str, database: str, columns: list = None) -> pd.DataFrame:
        if self.searcher:
            params, query = get_query_parameters(query)
            result = self.searcher.fuzzy_search(query, database=database)
            return self._meta_from_result(params, result, columns)

        # Fallback to simple pandas search
        logger.debug(f"Using simple pandas search for database '{database}' as searcher is not initialized.")
        return self._pandas_search(query, database=database, columns=columns)

    def _meta_from_result(self, params: dict, result: list[int], columns: list = None) -> pd.DataFrame:
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

        return df

    def auto_complete(self, word: str, context: Optional[set] = None, database: Optional[str] = None):
        if not self.searcher:
            logger.warning(f"Attempted to search metadata before searcher was initialized.")
            return []

        word = self.searcher.clean_text(word)
        completions = self.searcher.auto_complete(word, context=context, database=database)
        return completions

    def clear_cache(self):
        from activity_browser.bwutils import filesystem

        cache_path = filesystem.get_project_ab_path() / "metadatastore_cache.pkl"
        if cache_path.exists():
            cache_path.unlink()
            logger.info("Metadata store cache cleared.")
        else:
            logger.info("No metadata store cache found to clear.")


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
