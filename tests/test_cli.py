from otoe.cli import main


def test_cli_check_compiles_requested_path(tmp_path, capsys):
    module = tmp_path / "surface.py"
    module.write_text("value = 1\n", encoding="utf-8")

    result = main(["check", "--path", str(module)])

    captured = capsys.readouterr()
    assert result == 0
    assert f"compile {module}: ok" in captured.out


def test_cli_check_reports_compile_failure(tmp_path, capsys):
    module = tmp_path / "broken.py"
    module.write_text("def nope(:\n", encoding="utf-8")

    result = main(["check", "--path", str(module)])

    captured = capsys.readouterr()
    assert result == 1
    assert f"compile {module}: failed" in captured.out
