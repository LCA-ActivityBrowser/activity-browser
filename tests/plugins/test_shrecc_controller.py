"""SHRECC plugin controller unit tests."""
from ab_shrecc.controller import ShreccPluginController


def test_new_workflow_auto_numbered_labels():
    ctrl = ShreccPluginController(project_name_provider=lambda: "proj-a")
    w1 = ctrl.new_workflow()
    w2 = ctrl.new_workflow()
    assert w1.label == "Workflow 1"
    assert w2.label == "Workflow 2"
    assert w1.project_name == "proj-a"
    assert w2.project_name == "proj-a"


def test_duplicate_workflow_copies_config_only():
    ctrl = ShreccPluginController(project_name_provider=lambda: "proj-a")
    source = ctrl.new_workflow()
    source.config = {"countries": ["DE"]}
    source.create_succeeded_unwritten = True
    source.dirty = True

    dup = ctrl.duplicate_workflow(source.id)
    assert dup.config == {"countries": ["DE"]}
    assert not dup.create_succeeded_unwritten
    assert dup.dirty
    assert dup.project_name == "proj-a"


def test_should_confirm_close_when_dirty_or_unwritten():
    ctrl = ShreccPluginController(project_name_provider=lambda: "p")
    workflow = ctrl.new_workflow()
    assert not ctrl.should_confirm_close(workflow)

    workflow.dirty = True
    assert ctrl.should_confirm_close(workflow)

    workflow.dirty = False
    workflow.create_succeeded_unwritten = True
    assert ctrl.should_confirm_close(workflow)


def test_is_project_stale():
    ctrl = ShreccPluginController(project_name_provider=lambda: "current")
    workflow = ctrl.new_workflow()
    assert not ctrl.is_project_stale(workflow)

    workflow.project_name = "other"
    assert ctrl.is_project_stale(workflow)


def test_can_start_create_requires_complete_config_and_current_project():
    ctrl = ShreccPluginController(project_name_provider=lambda: "proj-a")
    workflow = ctrl.new_workflow()
    assert not ctrl.can_start_create(workflow)

    ctrl.update_config(
        workflow,
        {
            "years": [2021],
            "countries": ["DE"],
            "bg_db_name": "bg",
            "my_db_name": "out",
        },
    )
    assert ctrl.can_start_create(workflow)

    workflow.project_name = "other"
    assert not ctrl.can_start_create(workflow)


def test_build_new_database_kwargs_from_controller():
    ctrl = ShreccPluginController(project_name_provider=lambda: "proj-a")
    workflow = ctrl.new_workflow()
    ctrl.update_config(
        workflow,
        {
            "years": [2021],
            "countries": ["DE", "FR"],
            "bg_db_name": "bg",
            "my_db_name": "shrecc_out",
        },
    )
    kwargs = ctrl.build_new_database_kwargs(workflow)
    assert kwargs["project_name"] == "proj-a"
    assert kwargs["countries"] == ["DE", "FR"]
