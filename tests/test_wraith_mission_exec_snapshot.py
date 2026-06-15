import ast
import json
from pathlib import Path

import pytest

from examples.wraith import mission_exec_snapshot as mes
from examples.wraith.mission_exec_snapshot import (
    SCHEMA,
    format_elapsed,
    normalize_mission_exec_snapshot,
)

SOURCE_PATH = Path(mes.__file__)


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, "00:00:00"),
        ("not-a-number", "00:00:00"),
        (-5, "00:00:00"),
        (0, "00:00:00"),
        (76, "00:01:16"),
        (3661, "01:01:01"),
        ("76", "00:01:16"),
    ],
)
def test_format_elapsed_handles_edge_cases(value, expected):
    assert format_elapsed(value) == expected


def test_normalize_returns_schema_v0_by_default():
    snapshot = normalize_mission_exec_snapshot()
    assert snapshot["schema"] == SCHEMA == "wraith.ui.mission_exec.v0"


def test_normalize_preserves_unknown_schema():
    snapshot = normalize_mission_exec_snapshot({"schema": "wraith.ui.mission_exec.v9"})
    assert snapshot["schema"] == "wraith.ui.mission_exec.v9"


def test_normalize_output_is_json_sort_keys_serializable():
    snapshot = normalize_mission_exec_snapshot(
        mission={"name": "Demo"},
        status="ENGAGED",
        elapsed_seconds=76,
        logs=[{"lvl": "info", "msg": "hello"}],
        events=[{"sev": "ok", "msg": "world"}],
        pending_approval={"approval_id": "a1", "step_id": "s1"},
    )
    encoded = json.dumps(snapshot, sort_keys=True)
    assert json.loads(encoded) == snapshot


def test_normalize_fills_safe_defaults():
    snapshot = normalize_mission_exec_snapshot()

    assert snapshot["status"] == "PENDING"
    assert snapshot["elapsed"] == "00:00:00"
    assert snapshot["logs"] == []
    assert snapshot["events"] == []
    assert snapshot["preflight"] == []
    assert snapshot["pending_approval"] is None
    assert snapshot["mission"]["name"] == "NO ACTIVE MISSION"
    assert snapshot["mission"]["id"] == ""
    assert snapshot["mission"]["posture"] == ""
    assert snapshot["runtime_probe"] == {
        "frame": 0,
        "tone": "ok",
        "label": "Runtime snapshot ready",
        "last": "No live runtime mutation performed.",
    }


def test_elapsed_wins_over_elapsed_seconds_when_provided():
    snapshot = normalize_mission_exec_snapshot(elapsed="00:09:09", elapsed_seconds=76)
    assert snapshot["elapsed"] == "00:09:09"


def test_elapsed_seconds_formatted_when_only_source():
    snapshot = normalize_mission_exec_snapshot(elapsed_seconds=3661)
    assert snapshot["elapsed"] == "01:01:01"


def test_log_aliases_normalize_to_level_and_message():
    snapshot = normalize_mission_exec_snapshot(
        logs=[{"ts": "08:50:00", "lvl": "warn", "msg": "alias log"}]
    )
    log = snapshot["logs"][0]
    assert log == {
        "id": "l001",
        "ts": "08:50:00",
        "level": "warn",
        "message": "alias log",
    }


def test_event_aliases_normalize_to_severity_and_message():
    snapshot = normalize_mission_exec_snapshot(
        events=[{"ts": "08:50:00", "tag": "SCOPE", "sev": "warn", "msg": "alias event"}]
    )
    event = snapshot["events"][0]
    assert event == {
        "id": "e001",
        "ts": "08:50:00",
        "tag": "SCOPE",
        "severity": "warn",
        "message": "alias event",
    }


def test_missing_log_and_event_ids_are_autofilled():
    snapshot = normalize_mission_exec_snapshot(
        logs=[{"msg": "a"}, {"msg": "b"}],
        events=[{"msg": "x"}, {"msg": "y"}],
    )
    assert [line["id"] for line in snapshot["logs"]] == ["l001", "l002"]
    assert [event["id"] for event in snapshot["events"]] == ["e001", "e002"]
    assert snapshot["logs"][0]["level"] == "info"
    assert snapshot["events"][0]["severity"] == "ok"


def test_pending_approval_alias_normalizes_to_id():
    snapshot = normalize_mission_exec_snapshot(
        pending_approval={
            "approval_id": "approval-1",
            "step_id": "pivot",
            "summary": "waiting",
            "detail": "details",
        }
    )
    assert snapshot["pending_approval"] == {
        "id": "approval-1",
        "step_id": "pivot",
        "summary": "waiting",
        "detail": "details",
    }


def test_falsy_pending_approval_becomes_none():
    assert normalize_mission_exec_snapshot(pending_approval={})["pending_approval"] is None
    assert normalize_mission_exec_snapshot(pending_approval=None)["pending_approval"] is None


def test_pending_approval_forces_approve_and_deny_true():
    snapshot = normalize_mission_exec_snapshot(
        status="ABORTED",
        pending_approval={"approval_id": "a1"},
        actions={"can_approve": False, "can_deny": False},
    )
    assert snapshot["actions"]["can_approve"] is True
    assert snapshot["actions"]["can_deny"] is True


def test_terminal_status_disables_abort_and_pause():
    snapshot = normalize_mission_exec_snapshot(status="ABORTED")
    assert snapshot["actions"]["can_abort"] is False
    assert snapshot["actions"]["can_pause"] is False


def test_action_defaults_for_engaged_status():
    snapshot = normalize_mission_exec_snapshot(
        status="ENGAGED",
        logs=[{"msg": "a"}],
    )
    actions = snapshot["actions"]
    assert actions["can_abort"] is True
    assert actions["can_pause"] is True
    assert actions["can_resume"] is False
    assert actions["can_export"] is True
    assert actions["can_approve"] is False
    assert actions["can_deny"] is False


def test_paused_status_enables_resume():
    snapshot = normalize_mission_exec_snapshot(status="PAUSED")
    assert snapshot["actions"]["can_resume"] is True
    assert snapshot["actions"]["can_pause"] is False


def test_user_actions_override_non_approval_defaults():
    snapshot = normalize_mission_exec_snapshot(
        status="ENGAGED",
        actions={"can_export": True, "can_pause": False},
    )
    assert snapshot["actions"]["can_export"] is True
    assert snapshot["actions"]["can_pause"] is False


def test_inputs_are_not_mutated():
    logs = [{"lvl": "info", "msg": "a"}]
    events = [{"sev": "ok", "msg": "b"}]
    mission = {"name": "Demo"}
    pending = {"approval_id": "a1"}
    probe = {"frame": 2}

    normalize_mission_exec_snapshot(
        mission=mission,
        logs=logs,
        events=events,
        pending_approval=pending,
        runtime_probe=probe,
    )

    assert logs == [{"lvl": "info", "msg": "a"}]
    assert events == [{"sev": "ok", "msg": "b"}]
    assert mission == {"name": "Demo"}
    assert pending == {"approval_id": "a1"}
    assert probe == {"frame": 2}


class _Weird:
    def __repr__(self) -> str:
        return "<weird>"


def test_normalize_json_coerces_arbitrary_object_values():
    snapshot = normalize_mission_exec_snapshot(
        mission={"name": _Weird()},
        preflight=[{"label": _Weird()}],
        runtime_probe={"label": _Weird(), "tone": _Weird(), "last": _Weird()},
    )

    assert snapshot["mission"]["name"] == "<weird>"
    assert snapshot["preflight"][0]["label"] == "<weird>"
    assert snapshot["runtime_probe"]["label"] == "<weird>"
    assert snapshot["runtime_probe"]["tone"] == "<weird>"
    assert snapshot["runtime_probe"]["last"] == "<weird>"
    assert snapshot["runtime_probe"]["frame"] == 0


def test_normalize_preflight_nested_values_are_json_safe():
    snapshot = normalize_mission_exec_snapshot(
        preflight=[{"checks": [_Weird(), {"nested": _Weird()}]}]
    )

    preflight = snapshot["preflight"]
    assert preflight == [{"checks": ["<weird>", {"nested": "<weird>"}]}]
    json.dumps(preflight, sort_keys=True)


def test_normalize_does_not_mutate_object_valued_inputs():
    mission = {"name": _Weird()}
    preflight = [{"label": _Weird()}]
    probe = {"label": _Weird()}

    normalize_mission_exec_snapshot(
        mission=mission,
        preflight=preflight,
        runtime_probe=probe,
    )

    assert isinstance(mission["name"], _Weird)
    assert isinstance(preflight[0]["label"], _Weird)
    assert isinstance(probe["label"], _Weird)


def test_reproducer_output_is_json_dumps_serializable():
    snapshot = normalize_mission_exec_snapshot(
        mission={"name": _Weird()},
        preflight=[{"label": _Weird()}],
        runtime_probe={"label": _Weird(), "tone": _Weird(), "last": _Weird()},
    )

    encoded = json.dumps(snapshot, sort_keys=True)
    assert json.loads(encoded) == snapshot


def _imported_module_names() -> set[str]:
    tree = ast.parse(SOURCE_PATH.read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module)
    return names


def _top_level_imported_module_names() -> set[str]:
    tree = ast.parse(SOURCE_PATH.read_text())
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module)
    return names


def test_source_does_not_import_wraith():
    assert not any(name.split(".")[0] == "wraith" for name in _imported_module_names())


def test_source_does_not_import_kivy():
    assert not any(name.split(".")[0] == "kivy" for name in _imported_module_names())


def test_pure_path_does_not_import_otoe_at_module_level():
    assert not any(
        name.split(".")[0] == "otoe" for name in _top_level_imported_module_names()
    )
