# -*- coding: utf-8 -*-
from ast import literal_eval
from pathlib import Path
from typing import List, Union
from loguru import logger

import openpyxl
import pandas as pd

from .utils import SUPERSTRUCTURE
from .dataframe import ensure_string_scenario_names


def convert_tuple_str(x):
    try:
        return literal_eval(x)
    except (ValueError, SyntaxError) as e:
        return x


def get_sheet_names(document_path: Union[str, Path]) -> List[str]:
    try:
        with Path(document_path).open("rb") as f:
            wb = openpyxl.load_workbook(filename=f, read_only=True)
            return wb.sheetnames
    except UnicodeDecodeError as e:
        logger.error("Given document uses an unknown encoding: {}".format(e))


def valid_cols(name: str) -> bool:
    """True for data columns; names starting with '_' are SDF comment columns (not imported)."""
    return not str(name).startswith("_")


def _sdf_excel_skiprows(document_path: Union[str, Path], import_sheet: int) -> List[int]:
    """Row indices to skip so ``header=0`` lands on the SDF header.

    Skips leading non-header rows and any row whose first cell starts with ``#``.
    Header must appear within the first 10 rows (same rule as before).
    """
    with Path(document_path).open("rb") as f:
        wb = openpyxl.load_workbook(filename=f, read_only=True)
        try:
            sheet = wb.worksheets[import_sheet]
            header_idx = None
            hash_rows: List[int] = []
            for i, row in enumerate(
                sheet.iter_rows(min_col=1, max_col=1, values_only=True)
            ):
                value = row[0]
                if isinstance(value, str) and value.startswith("#"):
                    hash_rows.append(i)
                    continue
                if header_idx is None and isinstance(value, str):
                    header_idx = i
                if header_idx is None and i >= 9:
                    break
            if header_idx is None:
                raise ValueError(
                    "Could not find required headers in given document sheet."
                )
            return sorted(set(range(header_idx)) | set(hash_rows))
        finally:
            wb.close()


def import_from_excel(
    document_path: Union[str, Path], import_sheet: int = 1
) -> pd.DataFrame:
    """Import scenario exchanges from an Excel sheet.

    Comment rows (first cell starts with ``#``) and comment columns (name
    starts with ``_``) are excluded via ``skiprows`` / ``usecols`` — not
    pandas ``comment='#'``, which breaks Excel headers under openpyxl.
    """
    try:
        skiprows = _sdf_excel_skiprows(document_path, import_sheet)
        with Path(document_path).open("rb") as f:
            data = pd.read_excel(
                f,
                sheet_name=import_sheet,
                header=0,
                skiprows=skiprows or None,
                usecols=valid_cols,
                na_values="",
                keep_default_na=False,
                engine="openpyxl",
            )
        diff = SUPERSTRUCTURE.difference(data.columns)
        if not diff.empty:
            # Return the frame as-read so callers can report missing headers.
            # Do not run key converters that require a complete SUPERSTRUCTURE.
            return ensure_string_scenario_names(data)

        columns = ["from categories", "from key", "to categories", "to key"]
        data.loc[:, columns] = data[columns].map(convert_tuple_str)
        data = ensure_string_scenario_names(data)
        return data
    except Exception as e:
        logger.debug("Excel scenario import failed for sheet {}: {}", import_sheet, e)
        return pd.DataFrame({})
