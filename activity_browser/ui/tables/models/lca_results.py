# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from PySide2.QtCore import Qt

from activity_browser.i18n import _

from .base import PandasModel


RESULT_METADATA_HEADERS = (
    "index",
    "amount",
    "unit",
    "reference product",
    "name",
    "location",
    "database",
    "categories",
    "type",
    "code",
)


class ResultHeaderModel(PandasModel):
    """Translate only metadata columns whose positions are program-defined."""

    TRANSLATABLE_HEADERS = RESULT_METADATA_HEADERS

    def should_translate_header(self, section, value) -> bool:
        return section in getattr(self, "_translatable_header_sections", set())

    def set_leading_metadata_headers(self, maximum=None):
        """Record leading, non-numeric metadata columns by position.

        Contribution and inventory dataframes append numeric scientific result
        columns after their metadata. Position and dtype distinguish a built-in
        ``name`` header from a result column with the same spelling.
        """

        sections = set()
        columns = list(self._dataframe.columns)
        limit = len(columns) if maximum is None else min(maximum, len(columns))
        for section in range(limit):
            value = columns[section]
            if value not in self.TRANSLATABLE_HEADERS:
                break
            if pd.api.types.is_numeric_dtype(self._dataframe.iloc[:, section]):
                break
            sections.add(section)
        self._translatable_header_sections = sections


class LCAResultsModel(ResultHeaderModel):
    OVERVIEW_CORE_HEADERS = (
        "amount",
        "unit",
        "reference product",
        "name",
        "location",
        "database",
    )
    OVERVIEW_PREFIXES = (
        ("index",) + OVERVIEW_CORE_HEADERS,
        ("level_0", "level_1") + OVERVIEW_CORE_HEADERS,
    )

    def sync(self, df):
        self._dataframe = df.replace(np.nan, "", regex=True)
        columns = tuple(self._dataframe.columns)
        matched_prefix = next(
            (
                prefix
                for prefix in self.OVERVIEW_PREFIXES
                if columns[: len(prefix)] == prefix
            ),
            None,
        )
        # The fixed text metadata fields must also be non-numeric. This keeps a
        # scientific table with columns named ``amount``, ``name``, or
        # ``database`` from accidentally looking like the overview schema.
        if matched_prefix is not None:
            amount_section = matched_prefix.index("amount")
            text_sections = range(amount_section + 1, len(matched_prefix))
            if any(
                pd.api.types.is_numeric_dtype(self._dataframe.iloc[:, section])
                for section in text_sections
            ):
                matched_prefix = None

        self._translatable_header_sections = (
            {
                section
                for section, value in enumerate(matched_prefix)
                if value in self.TRANSLATABLE_HEADERS
            }
            if matched_prefix is not None
            else set()
        )
        self._has_unnamed_index_headers = (
            matched_prefix is not None
            and matched_prefix[:2] == ("level_0", "level_1")
        )
        self.updated.emit()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            value = self._dataframe.columns[section]
            if getattr(self, "_has_unnamed_index_headers", False):
                # ``reset_index`` gives unnamed MultiIndex levels these
                # implementation names.  Keep the dataframe/export untouched,
                # but present the two fixed overview fields meaningfully.
                if section == 0 and value == "level_0":
                    return _("database")
                if section == 1 and value == "level_1":
                    return _("code")
        return super().headerData(section, orientation, role)


class InventoryModel(ResultHeaderModel):

    def sync(self, df):
        self._dataframe = df
        # Inventory builders always place five metadata fields before the
        # dynamically named reference-flow result columns.
        self.set_leading_metadata_headers(maximum=5)
        # set the visible columns
        self.filterable_columns = {
            col: i for i, col in enumerate(self._dataframe.columns.to_list())
        }
        # set the columns te be defined as num (all except the first five for both biopshere and technosphere
        self.different_column_types = {
            col: "num"
            for i, col in enumerate(self._dataframe.columns.to_list())
            if i >= 5
        }
        self.updated.emit()


class ContributionModel(ResultHeaderModel):
    RESULT_LABELS = (
        "Score",
        "Total",
        "Rest (+)",
        "Rest (-)",
    )
    DISPLAY_UNITS = (
        "relative share",
        "units of each impact category",
    )
    TRANSLATABLE_VALUES = RESULT_LABELS + DISPLAY_UNITS

    def sync(self, df, unit="relative share", translate_unit=False):
        df = df.copy()
        self._translate_unit = translate_unit
        prefix = (
            tuple(str(value) for value in df["index"].iloc[:3])
            if "index" in df
            else ()
        )
        has_fixed_prefix = prefix in {
            ("Score", "Rest (+)", "Rest (-)"),
            ("Total", "Rest (+)", "Rest (-)"),
        }

        # Update only the object-valued metadata unit column. A numeric result
        # column with the same name is scientific data and must stay untouched.
        unit_sections = [
            section
            for section, value in enumerate(df.columns)
            if value == "unit"
            and not pd.api.types.is_numeric_dtype(df.iloc[:, section])
        ]
        if unit_sections:
            fixed_prefix_rows = 3 if has_fixed_prefix else 0
            df.iloc[:, unit_sections[0]] = [""] * fixed_prefix_rows + [unit] * (
                len(df) - fixed_prefix_rows
            )

        # Drop any rows where all numbers are 0. Remember which retained rows
        # came from the three built-in result rows so user data is never
        # translated merely because its spelling matches a fixed label.
        keep = ~(df.select_dtypes(include=np.number) == 0).all(axis=1)
        fixed_rows = (
            np.arange(len(df)) < min(3, len(df))
            if has_fixed_prefix
            else np.zeros(len(df), dtype=bool)
        )
        self._fixed_result_rows = {
            position
            for position, is_fixed in enumerate(fixed_rows[keep.to_numpy()])
            if is_fixed
        }
        self._dataframe = df.iloc[keep.to_numpy()]
        self.set_leading_metadata_headers()
        self.updated.emit()

    def should_translate_value(self, index, value: str) -> bool:
        column = self._dataframe.columns[index.column()]
        if column == "index":
            return (
                index.row() in getattr(self, "_fixed_result_rows", set())
                and value in self.RESULT_LABELS
            )
        if column == "unit":
            return (
                getattr(self, "_translate_unit", False)
                and value in self.DISPLAY_UNITS
            )
        return False
