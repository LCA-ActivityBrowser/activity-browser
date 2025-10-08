from time import time
from logging import getLogger
from typing import Literal

import pandas as pd

from qtpy.QtCore import Qt, QObject, Signal, SignalInstance, QTimer

from .fields import all, all_types


log = getLogger(__name__)


class MetaDataStore(QObject):
    synced: SignalInstance = Signal(set, set, set)  # added, updated, deleted

    def __init__(self, parent=None):
        from activity_browser import application
        from .loader import MDSLoader
        from .updater import MDSUpdater

        super().__init__(parent)

        self._dataframe = pd.DataFrame()

        self._added: set[tuple[str, str]] = set()
        self._updated: set[tuple[str, str]] = set()
        self._deleted: set[tuple[str, str]] = set()

        self.moveToThread(application.thread())

        self.loader = MDSLoader(self)
        self.updater = MDSUpdater(self)
        self.flusher: QTimer | None = None

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

        if not self.flusher:
            self.flusher = QTimer(self, interval=100)
            self.flusher.timeout.connect(self.flush_mutations)
            self.flusher.start()

    def flush_mutations(self):
        if not (self._added or self._updated or self._deleted):
            return

        t = time()
        self.synced.emit(self._added, self._updated, self._deleted)

        self._added.clear(), self._updated.clear(), self._deleted.clear()

        log.debug(f"Metadatastore sync signal completed in {time() - t:.2f} seconds")

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

AB_metadata = MetaDataStore()
