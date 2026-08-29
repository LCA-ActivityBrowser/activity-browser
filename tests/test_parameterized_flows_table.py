"""Parameterized Flows table follows Brightway's parameterized-flow index."""

from activity_browser import app  # noqa: F401  — ABApplication before pytest-qt's QApplication
from bw2data.parameters import ParameterizedExchange

from activity_browser.bwutils.parameters.formula_exchanges import (
    rebuild_parameterized_flow_index,
)


def test_parameterized_flows_table_follows_index_only(basic_database):
    from activity_browser.app.pages.parameters.parameterized_exchanges_section import (
        ParameterizedExchangesSection,
    )

    section = ParameterizedExchangesSection()
    ParameterizedExchange.delete().execute()
    assert len(section.build_exchanges_df()) == 0

    rebuild_parameterized_flow_index("basic")
    df = section.build_exchanges_df()
    assert len(df) == 1
    assert df.iloc[0]["formula"] == "5+5"
    assert df.iloc[0]["_exchange"] is not None


def test_app_database_write_handler_rebuilds_index(basic_database):
    from copy import deepcopy

    from bw2data.parameters import ParameterizedExchange
    from fixtures.basic import DATABASE

    ParameterizedExchange.delete().execute()
    basic_database.write(deepcopy(DATABASE), process=True, signal=True)
    assert [row.formula for row in ParameterizedExchange.select()] == ["5+5"]


def test_formula_delegate_paint_survives_locked_database(basic_database, monkeypatch, qtbot):
    from peewee import OperationalError
    from qtpy import QtCore, QtGui, QtWidgets

    from activity_browser.app.pages.parameters.parameterized_exchanges_section import (
        ParameterizedExchangesSection,
    )

    rebuild_parameterized_flow_index("basic")
    section = ParameterizedExchangesSection()
    qtbot.addWidget(section)
    section.sync()

    def locked(*args, **kwargs):
        raise OperationalError("database is locked")

    monkeypatch.setattr(
        "activity_browser.bwutils.commontasks.refresh_node",
        locked,
    )

    model = section.model
    formula_col = model.columns().index("formula")
    index = model.index(0, formula_col)
    assert index.isValid()

    from activity_browser.ui.delegates.new_formula import NewFormulaDelegate

    delegate = NewFormulaDelegate(section.view)
    option = QtWidgets.QStyleOptionViewItem()
    option.rect = QtCore.QRect(0, 0, 120, 24)
    option.state = QtWidgets.QStyle.State_None
    option.palette = section.view.palette()

    image = QtGui.QImage(120, 24, QtGui.QImage.Format_ARGB32)
    painter = QtGui.QPainter(image)
    try:
        delegate.paint(painter, option, index)
    finally:
        painter.end()
