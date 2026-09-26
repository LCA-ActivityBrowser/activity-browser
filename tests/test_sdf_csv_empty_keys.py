"""CSV scenario files with empty key cells (#1293).

An SDF may leave 'from key' / 'to key' empty; the keys are then looked up from
the name, product, location, categories and database columns. The CSV reader
has to hand those rows over the same way the Excel reader does.
"""

import math

import bw2data as bd
from bw2data.tests import bw2test
from openpyxl import Workbook

from activity_browser.bwutils.superstructure.excel import import_from_excel
from activity_browser.bwutils.superstructure.file_imports import ABCSVImporter
from activity_browser.bwutils.superstructure.manager import SuperstructureManager
from activity_browser.bwutils.superstructure.utils import SUPERSTRUCTURE

TECH_ROW = {
    "from activity name": "steel production",
    "from reference product": "steel",
    "from location": "GLO",
    "from categories": "",
    "from database": "db",
    "from key": "",
    "to activity name": "car production",
    "to reference product": "car",
    "to location": "GLO",
    "to categories": "",
    "to database": "db",
    "to key": "('db', 'car')",
    "flow type": "technosphere",
}
BIO_ROW = {
    "from activity name": "carbon dioxide",
    "from reference product": "",
    "from location": "",
    "from categories": "('air',)",
    "from database": "biosphere3",
    "from key": "",
    "to activity name": "car production",
    "to reference product": "car",
    "to location": "GLO",
    "to categories": "",
    "to database": "db",
    "to key": "",
    "flow type": "biosphere",
}
SCENARIOS = {"2025": 1.0, "2050": 2.0}


def _rows():
    return [TECH_ROW | SCENARIOS, BIO_ROW | SCENARIOS]


def _write_csv(path):
    cols = list(SUPERSTRUCTURE) + list(SCENARIOS)
    lines = [";".join(cols)]
    lines += [";".join(str(row[c]) for c in cols) for row in _rows()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_xlsx(path):
    cols = list(SUPERSTRUCTURE) + list(SCENARIOS)
    wb = Workbook()
    wb.active.title = "info"
    sheet = wb.create_sheet("scenarios")
    sheet.append(cols)
    for row in _rows():
        sheet.append([row[c] if row[c] != "" else None for c in cols])
    wb.save(path)


def _is_missing(value) -> bool:
    return isinstance(value, float) and math.isnan(value)


def test_csv_empty_key_cells_read_as_missing(tmp_path):
    path = tmp_path / "sdf.csv"
    _write_csv(path)

    df = ABCSVImporter.read_file(path, separator=";")

    assert _is_missing(df.loc[0, "from key"])
    assert df.loc[0, "to key"] == ("db", "car")
    assert _is_missing(df.loc[1, "from key"])
    assert _is_missing(df.loc[1, "to key"])


def test_csv_reads_keys_and_categories_like_excel(tmp_path):
    csv_path, xlsx_path = tmp_path / "sdf.csv", tmp_path / "sdf.xlsx"
    _write_csv(csv_path)
    _write_xlsx(xlsx_path)

    from_csv = ABCSVImporter.read_file(csv_path, separator=";")
    from_xlsx = import_from_excel(xlsx_path, import_sheet=1)

    for col in ["from key", "to key", "from categories", "to categories"]:
        for csv_value, xlsx_value in zip(from_csv[col], from_xlsx[col]):
            if _is_missing(xlsx_value):
                assert _is_missing(csv_value), col
            else:
                assert csv_value == xlsx_value, col
    assert from_csv.loc[1, "from categories"] == ("air",)


@bw2test
def test_csv_empty_keys_are_filled_from_the_databases(tmp_path):
    bd.Database(bd.config.biosphere).write(
        {
            (bd.config.biosphere, "co2"): {
                "name": "carbon dioxide",
                "categories": ("air",),
                "type": "emission",
                "unit": "kilogram",
            }
        }
    )
    bd.Database("db").write(
        {
            ("db", "steel"): {
                "name": "steel production",
                "reference product": "steel",
                "location": "GLO",
                "unit": "kilogram",
                "type": "process",
            },
            ("db", "car"): {
                "name": "car production",
                "reference product": "car",
                "location": "GLO",
                "unit": "unit",
                "type": "process",
            },
        }
    )
    path = tmp_path / "sdf.csv"
    _write_csv(path)

    df = ABCSVImporter.read_file(path, separator=";")
    df = SuperstructureManager.fill_empty_process_keys_in_exchanges(df)

    assert list(df["from key"]) == [("db", "steel"), (bd.config.biosphere, "co2")]
    assert list(df["to key"]) == [("db", "car"), ("db", "car")]
