import pytest
import bw2data as bd
from bw2data.errors import BW2Exception
from qtpy import QtWidgets

from activity_browser import actions



def test_launch_application(application_instance):
    """Test that the application launches correctly."""
    assert application_instance.main_window.isVisible()


def test_activity_delete(monkeypatch, basic_database):
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "warning",
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.Yes),
    )
    assert len(basic_database) == 4

    process = basic_database.get("process")

    actions.ActivityDelete.run([process.key])

    assert len(basic_database) == 1  # removed process and products

    with pytest.raises(BW2Exception):
        bd.get_activity(process.key)


def test_activity_duplicate(basic_database):
    assert len(basic_database) == 4

    process = basic_database.get("process")
    actions.ActivityDuplicate.run([process.key])

    assert len(basic_database) == 7



# def test_activity_graph(ab_app):
#     key = ("activity_tests", "3fcde3e3bf424e97b32cf29347ac7f33")
#     panel = ab_app.main_window.right_panel.tabs["Graph Explorer"]
#
#     assert projects.current == "default"
#     assert get_activity(key)
#     assert key not in panel.tabs
#
#     actions.ActivityGraph.run([key])
#
#     assert key in panel.tabs
#
#
def test_activity_new(monkeypatch, basic_database):
    from activity_browser.ui.widgets.new_node_dialog import NewNodeDialog

    monkeypatch.setattr(
        NewNodeDialog, "exec_", staticmethod(lambda *args, **kwargs: True)
    )

    monkeypatch.setattr(
        NewNodeDialog,
        "get_new_process_data",
        staticmethod(lambda *args, **kwargs: ("new_process", "new_product", "kg", "GLO"))
    )

    assert len(basic_database) == 4

    actions.ActivityNewProcess.run(basic_database.name)

    assert len(basic_database) == 6
    assert len([p for p in basic_database if p["name"] == "new_process"]) == 1
    assert len([p for p in basic_database if p["name"] == "new_product"]) == 1


def test_process_open(application_instance, basic_database):
    process = basic_database.get("process")

    actions.ActivityOpen.run([process.key])

    group = application_instance.main_window.centralWidget().groups["Activity Details"]
    assert "activity_details_basic_process" in [group.widget(i).objectName() for i in range(group.count())]


def test_product_open(application_instance, basic_database):
    product = basic_database.get("product_1")

    actions.ActivityOpen.run([product.key])

    group = application_instance.main_window.centralWidget().groups["Activity Details"]
    assert "activity_details_basic_process" in [group.widget(i).objectName() for i in range(group.count())]


# def test_activity_relink(ab_app, monkeypatch, qtbot):
#     key = ("activity_tests", "834c9010dff24c138c8ffa19924e5935")
#     from_key = ("db_to_relink_from", "6a98a991da90495ea599e35b3d3602ab")
#     to_key = ("db_to_relink_to", "0d4d83e3baee4b7e865c34a16a63f03e")
#
#     monkeypatch.setattr(
#         ActivityLinkingDialog, "exec_", staticmethod(lambda *args, **kwargs: True)
#     )
#
#     monkeypatch.setattr(
#         ActivityLinkingDialog, "relink", {"db_to_relink_from": "db_to_relink_to"}
#     )
#
#     assert projects.current == "default"
#     assert list(get_activity(key).exchanges())[1].input.key == from_key
#
#     actions.ActivityRelink.run([key])
#
#     assert list(get_activity(key).exchanges())[1].input.key == to_key
