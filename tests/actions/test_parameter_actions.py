import bw2data as bd
from bw2data.parameters import (ActivityParameter, DatabaseParameter,
                                ProjectParameter)
from PySide2 import QtWidgets

from activity_browser import actions
from activity_browser.actions.parameter.parameter_new import ParameterWizard


class TestParameterNew:
    def test_parameter_new_project(self, ab_app, monkeypatch):
        key = ("", "")
        param_data = {"name": "project_parameter_to_be_created", "amount": "1.0"}

        monkeypatch.setattr(
            ParameterWizard,
            "exec_",
            staticmethod(lambda *args, **kwargs: ParameterWizard.Accepted),
        )
        monkeypatch.setattr(ParameterWizard, "selected", 0)
        monkeypatch.setattr(ParameterWizard, "param_data", param_data)

        assert bd.projects.current == "default"
        assert "project_parameter_to_be_created" not in ProjectParameter.load().keys()

        actions.ParameterNew.run(key)

        assert "project_parameter_to_be_created" in ProjectParameter.load().keys()

    def test_parameter_new_database(self, ab_app, monkeypatch):
        key = ("db", "")
        param_data = {
            "name": "database_parameter_to_be_created",
            "database": "activity_tests",
            "amount": "1.0",
        }

        monkeypatch.setattr(
            ParameterWizard,
            "exec_",
            staticmethod(lambda *args, **kwargs: ParameterWizard.Accepted),
        )
        monkeypatch.setattr(ParameterWizard, "selected", 1)
        monkeypatch.setattr(ParameterWizard, "param_data", param_data)

        assert bd.projects.current == "default"
        assert (
            "database_parameter_to_be_created"
            not in DatabaseParameter.load("activity_tests").keys()
        )

        actions.ParameterNew.run(key)

        assert (
            "database_parameter_to_be_created"
            in DatabaseParameter.load("activity_tests").keys()
        )

    def test_parameter_new_activity(self, ab_app, monkeypatch):
        key = ("activity_tests", "3fcde3e3bf424e97b32cf29347ac7f33")
        group = "activity_group"
        param_data = {
            "name": "activity_parameter_to_be_created",
            "database": key[0],
            "code": key[1],
            "group": group,
            "amount": "1.0",
        }

        monkeypatch.setattr(
            ParameterWizard,
            "exec_",
            staticmethod(lambda *args, **kwargs: ParameterWizard.Accepted),
        )
        monkeypatch.setattr(ParameterWizard, "selected", 2)
        monkeypatch.setattr(ParameterWizard, "param_data", param_data)

        assert bd.projects.current == "default"
        assert (
            "activity_parameter_to_be_created"
            not in ActivityParameter.load(group).keys()
        )

        actions.ParameterNew.run(key)

        assert (
            "activity_parameter_to_be_created" in ActivityParameter.load(group).keys()
        )

    def test_parameter_new_wizard_project(self, ab_app):
        key = ("", "")
        param_data = {"name": "parameter_test", "amount": "1.0"}
        wizard = ParameterWizard(key)

        assert not wizard.isVisible()
        wizard.show()
        assert wizard.isVisible()
        assert wizard.pages[0].isVisible()
        assert wizard.pages[0].selected == 0
        wizard.next()
        assert wizard.pages[1].isVisible()
        assert wizard.pages[1].database.isHidden()
        wizard.pages[1].name.setText("parameter_test")
        wizard.done(1)
        assert not wizard.isVisible()
        assert wizard.param_data == param_data

    def test_parameter_new_wizard_parameter(self, ab_app):
        key = ("db", "")
        param_data = {
            "name": "parameter_test",
            "database": "activity_tests",
            "amount": "1.0",
        }
        wizard = ParameterWizard(key)

        assert not wizard.isVisible()
        wizard.show()
        assert wizard.isVisible()
        assert wizard.pages[0].isVisible()
        assert wizard.pages[0].selected == 1
        wizard.next()
        assert wizard.pages[1].isVisible()
        assert not wizard.pages[1].database.isHidden()
        wizard.pages[1].name.setText("parameter_test")
        wizard.pages[1].database.setCurrentText("activity_tests")
        wizard.done(1)
        assert not wizard.isVisible()
        assert wizard.param_data == param_data

    def test_parameter_new_wizard_activity(self, ab_app):
        key = ("activity_tests", "be8fb2776c354aa7ad61d8348828f3af")
        param_data = {
            "name": "parameter_test",
            "database": "activity_tests",
            "code": "be8fb2776c354aa7ad61d8348828f3af",
            "group": "4748",
            "amount": "1.0",
        }
        wizard = ParameterWizard(key)

        assert not wizard.isVisible()
        wizard.show()
        assert wizard.isVisible()
        assert wizard.pages[0].isVisible()
        assert wizard.pages[0].selected == 2
        wizard.next()
        assert wizard.pages[1].isVisible()
        assert wizard.pages[1].database.isHidden()
        wizard.pages[1].name.setText("parameter_test")
        wizard.done(1)
        assert not wizard.isVisible()
        assert wizard.param_data == param_data


def test_parameter_new_automatic(ab_app):
    key = ("activity_tests", "dd4e2393573c49248e7299fbe03a169c_copy1")
    group = bd.get_activity(key)._document.id

    assert bd.projects.current == "default"
    assert "dummy_parameter" not in ActivityParameter.load(group).keys()

    actions.ParameterNewAutomatic.run([key])

    assert "dummy_parameter" in ActivityParameter.load(group).keys()


def test_parameter_rename(ab_app, monkeypatch):
    parameter = list(
        ProjectParameter.select().where(ProjectParameter.name == "parameter_to_rename")
    )[0]

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: ("renamed_parameter", True)),
    )

    assert bd.projects.current == "default"
    assert "renamed_parameter" not in ProjectParameter.load().keys()

    actions.ParameterRename.run(parameter)

    assert "parameter_to_rename" not in ProjectParameter.load().keys()
    assert "renamed_parameter" in ProjectParameter.load().keys()
