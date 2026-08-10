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


def get_header_index(document_path: Union[str, Path], import_sheet: int):
    """Retrieves the line index for the column headers, will raise an
    exception if not found in the first 10 rows.
    """
    try:
        with Path(document_path).open("rb") as f:
            wb = openpyxl.load_workbook(filename=f, read_only=True)
            sheet = wb.worksheets[import_sheet]
            for i in range(10):
                value = sheet.cell(i + 1, 1).value
                # Skip SDF comment rows (first cell starts with '#').
                if isinstance(value, str) and not value.startswith("#"):
                    wb.close()
                    return i
    except IndexError as e:
        wb.close()
        raise IndexError("Expected headers not found in file").with_traceback(
            e.__traceback__
        )
    except UnicodeDecodeError as e:
        logger.error("Given document uses an unknown encoding: {}".format(e))
        wb.close()
    raise ValueError("Could not find required headers in given document sheet.")


def valid_cols(name: str) -> bool:
    """True for data columns; names starting with '_' are SDF comment columns (not imported)."""
    return not str(name).startswith("_")


def import_from_excel(
    document_path: Union[str, Path], import_sheet: int = 1
) -> pd.DataFrame:
    """Import all of the exchanges and their scenario amounts from a given
    document and sheet index.

    The default index chosen represents the second sheet (first after the
    'information' sheet).

    Comment rows: a '#' at the start of a row (pandas ``comment='#'``).
    Comment columns: a column name starting with '_' (``usecols=valid_cols``).
    """
    data = pd.DataFrame({})
    try:
        header_idx = get_header_index(document_path, import_sheet)
        with Path(document_path).open("rb") as f:
            data = pd.read_excel(
                f,
                sheet_name=import_sheet,
                header=header_idx,
                usecols=valid_cols,
                comment="#",
                na_values="",
                keep_default_na=False,
                engine="openpyxl",
            )
        diff = SUPERSTRUCTURE.difference(data.columns)
        if not diff.empty:
            raise ValueError(
                "Missing required column(s) for superstructure: {}".format(
                    diff.to_list()
                )
            )

        # Convert specific columns that may have tuples as strings
        columns = ["from categories", "from key", "to categories", "to key"]
        data.loc[:, columns] = data[columns].map(convert_tuple_str)
        # Scenario headers typed as numbers in Excel (e.g. 2025) must be strings.
        data = ensure_string_scenario_names(data)
    except Exception as e:
        # Caller (UI) decides how to surface failures; empty frame means "not this sheet".
        logger.debug("Excel scenario import failed for sheet {}: {}", import_sheet, e)
    return data
