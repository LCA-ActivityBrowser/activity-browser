"""SDF comments: '#' rows (pandas comment=) and '_' columns (usecols).

Keep this file free of Excel/openpyxl I/O so it stays cheap in CI.
Excel uses the same pandas knobs; column rule is covered by ``valid_cols``.
"""
from activity_browser.bwutils.superstructure.excel import valid_cols
from activity_browser.bwutils.superstructure.file_imports import ABCSVImporter
from activity_browser.bwutils.superstructure.utils import SUPERSTRUCTURE


def test_valid_cols_drops_underscore_prefix():
    assert valid_cols("_notes") is False
    assert valid_cols("2025") is True
    assert valid_cols("from database") is True


def test_csv_hash_rows_and_underscore_columns(tmp_path):
    cols = list(SUPERSTRUCTURE) + ["_notes", "2025"]
    header = ";".join(cols)
    data = (
        "A;p;GLO;;db1;('db1', 'a');B;q;GLO;;db2;('db2', 'b');technosphere;x;1.0"
    )
    text = "\n".join(
        [
            "# leading file comment",
            header,
            data,
            "# skipped data row",
        ]
    )
    path = tmp_path / "sdf.csv"
    path.write_text(text, encoding="utf-8")

    df = ABCSVImporter.read_file(path, separator=";")

    assert list(df.columns) == cols[:-2] + ["2025"]  # _notes dropped
    assert "_notes" not in df.columns
    assert len(df) == 1
    assert df.loc[0, "from database"] == "db1"
    assert float(df.loc[0, "2025"]) == 1.0
