"""Impact-category template path/copy smoke tests."""
from pathlib import Path

from activity_browser.bwutils.impact_categories.templates import (
    TEMPLATE_FILES,
    copy_impact_category_template,
    template_paths,
)


def test_impact_category_template_paths_exist():
    for kind in TEMPLATE_FILES:
        paths = template_paths(kind)
        assert paths
        assert all(p.is_file() for p in paths)


def test_copy_ab_xlsx_template(tmp_path: Path):
    dest = tmp_path / "out.xlsx"
    written = copy_impact_category_template("ab-xlsx", dest)
    assert len(written) == 1
    assert written[0].is_file()


def test_copy_ab_csv_template_pair(tmp_path: Path):
    written = copy_impact_category_template("ab-csv", tmp_path / "my-lcia")
    assert len(written) == 2
    assert all(p.is_file() for p in written)
