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


def test_pristine_workflow_auto_syncs_to_current_project():
    project = {"name": "proj-a"}
    ctrl = ShreccPluginController(project_name_provider=lambda: project["name"])
    workflow = ctrl.new_workflow()
    assert workflow.project_name == "proj-a"

    project["name"] = "proj-b"
    updated = ctrl.sync_pristine_workflows_to_current()
    assert updated == [workflow.id]
    assert workflow.project_name == "proj-b"
    assert not ctrl.is_project_stale(workflow)


def test_switch_to_current_project_keeps_config_clears_create():
    project = {"name": "proj-a"}
    ctrl = ShreccPluginController(project_name_provider=lambda: project["name"])
    workflow = ctrl.new_workflow()
    ctrl.update_config(
        workflow,
        {
            "years": [2021],
            "countries": ["DE"],
            "bg_db_name": "bg",
            "my_db_name": "out",
        },
    )
    ctrl.complete_create(workflow, object(), {"years": [2021]})
    project["name"] = "proj-b"
    assert ctrl.is_project_stale(workflow)
    assert not ctrl.is_pristine(workflow)

    assert ctrl.switch_to_current_project(workflow)
    assert workflow.project_name == "proj-b"
    assert workflow.create_status == "idle"
    assert workflow.create_handle is None
    assert workflow.config["countries"] == ["DE"]
    assert not ctrl.is_project_stale(workflow)


def test_sync_does_not_auto_rebind_workflows_with_results():
    project = {"name": "proj-a"}
    ctrl = ShreccPluginController(project_name_provider=lambda: project["name"])
    workflow = ctrl.new_workflow()
    ctrl.complete_create(workflow, object(), {"years": [2021]})
    project["name"] = "proj-b"
    assert ctrl.sync_pristine_workflows_to_current() == []
    assert workflow.project_name == "proj-a"
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


def test_one_job_lock_blocks_second_create():
    ctrl = ShreccPluginController(project_name_provider=lambda: "proj-a")
    w1 = ctrl.new_workflow()
    w2 = ctrl.new_workflow()
    _fill_complete_config(ctrl, w1)
    _fill_complete_config(ctrl, w2)

    ctrl.begin_create(w1)
    assert ctrl.can_start_create(w1) is False
    assert ctrl.can_start_create(w2) is False


def test_mark_inspect_stale_on_config_change_after_create():
    ctrl = ShreccPluginController(project_name_provider=lambda: "proj-a")
    workflow = ctrl.new_workflow()
    _fill_complete_config(ctrl, workflow)
    ctrl.complete_create(workflow, object(), {"years": [2021]})

    ctrl.update_config(workflow, {"my_db_name": "changed"})
    assert workflow.create_status == "stale"
    assert ctrl.can_start_write(workflow) is False


def test_can_start_write_requires_done_create_and_current_project():
    ctrl = ShreccPluginController(project_name_provider=lambda: "proj-a")
    workflow = ctrl.new_workflow()
    _fill_complete_config(ctrl, workflow)
    ctrl.complete_create(workflow, object(), {"years": [2021]})
    assert ctrl.can_start_write(workflow)

    workflow.project_name = "other"
    assert not ctrl.can_start_write(workflow)


def test_can_rewrite_after_successful_write():
    ctrl = ShreccPluginController(project_name_provider=lambda: "proj-a")
    workflow = ctrl.new_workflow()
    _fill_complete_config(ctrl, workflow)
    handle = object()
    ctrl.complete_create(workflow, handle, {"years": [2021]})
    ctrl.complete_write(workflow, {2021: "out-db"})
    assert not workflow.create_succeeded_unwritten
    assert ctrl.can_start_write(workflow)


def test_one_job_lock_blocks_write_while_create_running():
    ctrl = ShreccPluginController(project_name_provider=lambda: "proj-a")
    workflow = ctrl.new_workflow()
    _fill_complete_config(ctrl, workflow)
    ctrl.begin_create(workflow)
    assert not ctrl.can_start_write(workflow)


def test_write_lifecycle_complete_and_fail():
    ctrl = ShreccPluginController(project_name_provider=lambda: "proj-a")
    workflow = ctrl.new_workflow()
    _fill_complete_config(ctrl, workflow)
    ctrl.complete_create(workflow, object(), {"years": [2021]})

    ctrl.begin_write(workflow)
    assert ctrl.global_job == "write"
    ctrl.complete_write(workflow, {2021: "out"})
    assert workflow.write_status == "done"
    assert workflow.written_database_names == {2021: "out"}
    assert ctrl.global_job is None

    ctrl.begin_write(workflow)
    ctrl.fail_write(workflow, "boom", {2021: "out"})
    assert workflow.write_status == "failed"
    assert workflow.partial_written_names == {2021: "out"}


def test_job_status_text_reflects_global_job():
    ctrl = ShreccPluginController(project_name_provider=lambda: "proj-a")
    workflow = ctrl.new_workflow()
    assert ctrl.job_status_text() == "App job: idle"

    ctrl.begin_create(workflow)
    assert "create" in ctrl.job_status_text()
    assert "Workflow 1" in ctrl.job_status_text()

    ctrl.complete_create(workflow, object(), {})
    ctrl.begin_write(workflow)
    assert "write" in ctrl.job_status_text()


def test_one_job_lock_blocks_write_on_other_workflow():
    ctrl = ShreccPluginController(project_name_provider=lambda: "proj-a")
    w1 = ctrl.new_workflow()
    w2 = ctrl.new_workflow()
    _fill_complete_config(ctrl, w1)
    _fill_complete_config(ctrl, w2)
    ctrl.complete_create(w1, object(), {"years": [2021]})
    ctrl.complete_create(w2, object(), {"years": [2021]})

    ctrl.begin_write(w1)
    assert not ctrl.can_start_write(w2)


def test_mark_inspect_stale_clears_create_handle_keeps_artifacts():
    ctrl = ShreccPluginController(project_name_provider=lambda: "proj-a")
    workflow = ctrl.new_workflow()
    _fill_complete_config(ctrl, workflow)
    artifacts = {"years": [2021], "summary": [{"year": 2021}]}
    ctrl.complete_create(workflow, object(), artifacts)
    assert workflow.create_handle is not None

    ctrl.mark_inspect_stale(workflow)
    assert workflow.create_status == "stale"
    assert workflow.create_handle is None
    assert workflow.inspect_artifacts == artifacts
    assert not ctrl.can_start_write(workflow)
    assert ctrl.is_inspect_stage_available(workflow)
    assert not ctrl.is_write_stage_available(workflow)


def test_stage_availability_and_create_action_label():
    ctrl = ShreccPluginController(project_name_provider=lambda: "proj-a")
    workflow = ctrl.new_workflow()
    assert not ctrl.is_inspect_stage_available(workflow)
    assert not ctrl.is_write_stage_available(workflow)
    assert ctrl.create_action_label(workflow) == "Create"
    assert ctrl.write_action_label(workflow) == "Write"

    _fill_complete_config(ctrl, workflow)
    artifacts = {"years": [2021], "summary": [{"year": 2021}]}
    ctrl.complete_create(workflow, object(), artifacts)
    assert ctrl.is_inspect_stage_available(workflow)
    assert ctrl.is_write_stage_available(workflow)
    assert ctrl.create_action_label(workflow) == "Create"
    assert ctrl.write_action_label(workflow) == "Write"

    ctrl.complete_write(workflow, {2021: "out"})
    assert ctrl.write_action_label(workflow) == "Write again"

    ctrl.fail_write(workflow, "boom", {})
    assert ctrl.write_action_label(workflow) == "Write again"

    ctrl.update_config(workflow, {"my_db_name": "changed"})
    assert workflow.create_status == "stale"
    assert ctrl.is_inspect_stage_available(workflow)
    assert not ctrl.is_write_stage_available(workflow)
    assert ctrl.create_action_label(workflow) == "Create again"

    ctrl.begin_create(workflow)
    assert workflow.inspect_artifacts == artifacts
    ctrl.fail_create(workflow, "boom")
    assert workflow.inspect_artifacts == artifacts
    assert ctrl.is_inspect_stage_available(workflow)
    assert not ctrl.is_write_stage_available(workflow)
    assert ctrl.create_action_label(workflow) == "Create again"

    fresh = ctrl.new_workflow()
    _fill_complete_config(ctrl, fresh)
    ctrl.begin_create(fresh)
    ctrl.fail_create(fresh, "first fail")
    assert not fresh.inspect_artifacts
    assert not ctrl.is_inspect_stage_available(fresh)


def test_remove_workflow_clears_global_job():
    ctrl = ShreccPluginController(project_name_provider=lambda: "proj-a")
    workflow = ctrl.new_workflow()
    ctrl.begin_create(workflow)
    ctrl.remove_workflow(workflow.id)
    assert ctrl.global_job is None


def test_should_confirm_close_false_after_write():
    ctrl = ShreccPluginController(project_name_provider=lambda: "proj-a")
    workflow = ctrl.new_workflow()
    _fill_complete_config(ctrl, workflow)
    ctrl.complete_create(workflow, object(), {"years": [2021]})
    ctrl.complete_write(workflow, {2021: "out"})
    workflow.dirty = False
    assert not ctrl.should_confirm_close(workflow)


def test_config_change_before_create_does_not_mark_stale():
    ctrl = ShreccPluginController(project_name_provider=lambda: "proj-a")
    workflow = ctrl.new_workflow()
    _fill_complete_config(ctrl, workflow)
    ctrl.update_config(workflow, {"my_db_name": "other"})
    assert workflow.create_status == "idle"


def _fill_complete_config(ctrl, workflow):
    ctrl.update_config(
        workflow,
        {
            "years": [2021],
            "countries": ["DE"],
            "bg_db_name": "bg",
            "my_db_name": "out",
        },
    )
