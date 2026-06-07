from __future__ import annotations

from otoe.build_runner import build_runner_source


def test_build_runner_source_generates_compileable_template():
    source = build_runner_source(
        {"native": ("framework/otoe/__init__.py",)}
    )

    assert "__OTOE_EXPECTED_FRAMEWORK_FILES__" not in source
    assert "EXPECTED_FRAMEWORK_FILES = {'native':" in source
    compile(source, "otoe-run.py", "exec")
