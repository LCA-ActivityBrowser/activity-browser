# -*- coding: utf-8 -*-
import numbers
from pathlib import Path
from typing import Union

import brightway2 as bw
from bw2data.utils import safe_filename
from bw2io.export.excel import CSVFormatter, create_valid_worksheet_name
import xlsxwriter

from .pedigree import PedigreeMatrix

# Copied most of this code wholesale from bw2io package.
# TODO: reminder to make a pull-request for these things in bw2io repo.
#  - Add the 'nan_inf_to_errors' option when opening the xlsxwriter.Workbook.
#  - Add handler for pedigree data to exporter


def format_pedigree(data: dict) -> str:
    """Converts pedigree dict to tuple."""
    try:
        return "::".join(str(x) for x in PedigreeMatrix.from_dict(data).factors_as_tuple())
    except AssertionError:
        # Will skip any other kinds of dictionaries.
        return 'nan'


def frmt_str(data: Union[str, dict]) -> str:
    return format_pedigree(data) if isinstance(data, dict) else data


def write_lci_excel(db_name: str, path: str, objs=None, sections=None) -> Path:
    """Export database `database_name` to an Excel spreadsheet.

    Not all data can be exported. The following constraints apply:

    * Nested data, e.g. `{'foo': {'bar': 'baz'}}` are excluded. Spreadsheets are not a great format for nested data. However, *tuples* are exported, and the characters `::` are used to join elements of the tuple.
    * The only well-supported data types are strings, numbers, and booleans.

    Returns the filepath of the exported file.

    """
    path = Path(path)
    if not path.suffix == ".xlsx":
        out_file = path / "lci-{}.xlsx".format(safe_filename(db_name, False))
    else:
        out_file = path

    workbook = xlsxwriter.Workbook(out_file, {'nan_inf_to_errors': True})
    bold = workbook.add_format({'bold': True})
    bold.set_font_size(12)
    highlighted = {'Activity', 'Database', 'Exchanges', 'Parameters', 'Database parameters', 'Project parameters'}
    frmt = lambda x: bold if row[0] in highlighted else None

    sheet = workbook.add_worksheet(create_valid_worksheet_name(db_name))

    data = CSVFormatter(db_name, objs).get_formatted_data(sections)

    for row_index, row in enumerate(data):
        for col_index, value in enumerate(row):
            if value is None:
                continue
            elif isinstance(value, numbers.Number):
                sheet.write_number(row_index, col_index, value, frmt(value))
            else:
                sheet.write_string(row_index, col_index, frmt_str(value), frmt(value))

    workbook.close()

    return out_file
