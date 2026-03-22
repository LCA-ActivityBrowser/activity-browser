import numbers
import json
from datetime import datetime as dt
from pathlib import Path
from typing import Union

import xlsxwriter
from bw2io.export.csv import reformat
from bw2io.export.excel import CSVFormatter, create_valid_worksheet_name

from activity_browser.mod import bw2data as bd

from .importers import ABPackage
from .pedigree import PedigreeMatrix

# Copied most of this code wholesale from bw2io package.
# TODO: reminder to make a pull-request for these things in bw2io repo.
#  - Add the 'nan_inf_to_errors' option when opening the xlsxwriter.Workbook.
#  - Add handler for pedigree data to exporter
#  - Add 'database' field as required CSVFormatter export field.
#  - Add code to ensure no second 'activity' field is exported, as this
#  messes with following import.


def ab_reformat(value):
    if isinstance(value, dict):
        try:
            return json.dumps(value)
        except TypeError:
            return "Non-serializable dictionary"
    return reformat(value)


class ABCSVFormatter(CSVFormatter):
    def get_activity_metadata(self, act):
        excluded = {"database", "name", "activity"}
        return {
            "name": act.get("name"),
            "metadata": sorted(
                [
                    (k, ab_reformat(v))
                    for k, v in act.items()
                    if k not in excluded and not isinstance(v, list)
                ]
            ),
            "parameters": self.get_activity_parameters(act),
        }

    def exchange_as_dict(self, exc):
        """Same as CSVFormatter, but explicitly pull the database from the
        input activity.

        This ensures that the database value is always included, even when
        it is not stored in the exchange _data.
        """
        inp = exc.input
        inp_fields = (
            "name",
            "unit",
            "location",
            "categories",
            "database",
            "reference product",
        )
        skip_fields = ("input", "output")
        data = {k: v for k, v in exc._data.items() if k not in skip_fields}
        if "product" in data and "reference product" not in data:
            data["reference product"] = data.pop("product")
        data.update(**{k: inp[k] for k in inp_fields if inp.get(k)})
        return data


def format_pedigree(data: dict) -> str:
    """Converts pedigree dict to tuple."""
    try:
        return "::".join(
            str(x) for x in PedigreeMatrix.from_dict(data).factors_as_tuple()
        )
    except AssertionError:
        # Will skip any other kinds of dictionaries.
        return "nan"


def frmt_str(data: Union[str, dict]) -> str:
    """Format non-numerical data (like tuples) to string format."""
    return format_pedigree(data) if isinstance(data, dict) else str(data)


def write_lci_excel(db_name: str, path: str, objs=None, sections=None) -> Path:
    """Export database `database_name` to an Excel spreadsheet.

    Not all data can be exported. The following constraints apply:

    * Nested data, e.g. `{'foo': {'bar': 'baz'}}` are excluded. Spreadsheets are not a great format for nested data.
      However, *tuples* are exported, and the characters `::` are used to join elements of the tuple.
    * The only well-supported data types are strings, numbers, and booleans.

    Returns the filepath of the exported file.

    """
    path = Path(path)
    if not path.suffix == ".xlsx":
        out_file = path / "lci-{}.xlsx".format(bd.utils.safe_filename(db_name, False))
    else:
        out_file = path

    workbook = xlsxwriter.Workbook(out_file, {"nan_inf_to_errors": True})
    bold = workbook.add_format({"bold": True})
    bold.set_font_size(12)
    highlighted = {
        "Activity",
        "Database",
        "Exchanges",
        "Parameters",
        "Database parameters",
        "Project parameters",
    }
    frmt = lambda x: bold if row[0] in highlighted else None

    sheet = workbook.add_worksheet(create_valid_worksheet_name(db_name))

    data = ABCSVFormatter(db_name, objs).get_formatted_data(sections)

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


def store_database_as_package(db_name: str, directory: str = None) -> bool:
    """Attempt to use `bw.BW2Package` to save the given database as an
    isolated package that can be shared with others.
    Returns a boolean signifying success or failure.
    """
    if db_name not in bd.databases:
        return False
    metadata = bd.databases[db_name]
    db = bd.Database(db_name)
    directory = directory or bd.projects.output_dir
    output_dir = Path(directory)
    if output_dir.suffix == ".bw2package":
        out_file = output_dir
    else:
        out_file = output_dir / "{}.bw2package".format(db.filename)
    # First, ensure the metadata on the database is up-to-date.
    modified = dt.strptime(metadata["modified"], "%Y-%m-%dT%H:%M:%S.%f")
    if "processed" in metadata:
        processed = dt.strptime(metadata["processed"], "%Y-%m-%dT%H:%M:%S.%f")
        if processed < modified:
            db.process()
    else:
        db.process()
    # Now that processing is done, perform the export.
    ABPackage.unrestricted_export(db, out_file)
    return True
