from pathlib import Path

from examples.wraith_input_console import WraithInputConsoleDemo, app, load_stylesheet
from otoe import mount, render_html
from otoe.cli import main


ROOT = Path(__file__).resolve().parents[1]
STYLES = ROOT / "preview" / "wraith_input_console.css"


def test_wraith_input_console_html_render_smoke():
    html = render_html(mount(app()), stylesheet=load_stylesheet(), pretty=True)

    assert "Wraith Input Console" in html
    assert "Dry Run" in html
    assert "Execute" in html
    assert "Safe Mode" in html
    assert "Thermal Guard" in html
    assert "console booted in portable input mode" in html


def test_wraith_input_console_native_click_primary_action_adds_log():
    demo = WraithInputConsoleDemo()

    demo.click_text("Dry Run")

    assert demo.model.runtime_status.value == "Dry run queued"
    assert demo.model.logs.value[-1].message == "dry run queued for WR-018"
    assert "Dry run queued" in demo.visible_texts()


def test_wraith_input_console_keyboard_tab_and_enter_activate_button():
    demo = WraithInputConsoleDemo()

    focused = _tab_to_focused_text(demo, "Dry Run")
    demo.key_down("Enter")

    assert focused == "Dry Run"
    assert demo.model.runtime_status.value == "Dry run queued"
    assert demo.model.logs.value[-1].severity == "ok"


def test_wraith_input_console_escape_dismisses_execute_confirm():
    demo = WraithInputConsoleDemo()

    demo.click_text("Execute")
    assert demo.model.confirm_open.value is True
    assert "Confirm Execute" in demo.visible_texts()

    demo.key_down("Escape")

    assert demo.model.confirm_open.value is False
    assert "Confirm Execute" not in demo.visible_texts()


def test_wraith_input_console_confirm_execute_commits_action():
    demo = WraithInputConsoleDemo()

    demo.click_text("Execute")
    assert demo.model.confirm_open.value is True

    demo.click_text("Confirm Execute")

    assert demo.model.confirm_open.value is False
    assert demo.model.runtime_status.value == "Executing"
    assert demo.model.logs.value[-1].message == "confirmed execute for WR-018"


def test_wraith_input_console_ctrl_k_opens_command_panel():
    demo = WraithInputConsoleDemo()

    demo.key_down("k", ctrl=True)

    assert demo.model.command_open.value is True
    assert "Command panel" in demo.visible_texts()


def test_wraith_input_console_build_validate_smoke(tmp_path, capsys):
    output = tmp_path / "wraith-input-console"

    result = main(
        [
            "build",
            "examples.wraith_input_console:app",
            "--out",
            str(output),
            "--css",
            str(STYLES),
            "--validate",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "validation: ok" in captured.out
    assert (output / "manifest.json").exists()


def _tab_to_focused_text(demo: WraithInputConsoleDemo, text: str) -> str:
    for _ in range(30):
        demo.key_down("Tab")
        focused = demo.surface.focused_box
        if focused is not None and focused.text == text:
            return focused.text
    focused_text = None if demo.surface.focused_box is None else demo.surface.focused_box.text
    raise AssertionError(f"Could not tab to {text!r}; focused {focused_text!r}.")
