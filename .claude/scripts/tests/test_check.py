import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check  # noqa: E402


def test_build_commands_includes_static_and_unit_gates():
    commands = check.build_commands(skip_regression=True)
    names = [command.name for command in commands]

    assert names == ["pytest", "python syntax", "shell syntax"]
    assert ".claude/scripts/tests" in commands[0].argv
    assert "-m" in commands[1].argv
    assert "py_compile" in commands[1].argv
    assert "bash" == commands[2].argv[0]
    assert "-n" == commands[2].argv[1]


def test_python_compile_patterns_cover_release_scripts():
    paths = check.expand_patterns(check.PY_COMPILE_PATTERNS)

    assert ".claude/scripts/run-regression.py" in paths
    assert ".claude/scripts/check.py" in paths
    assert ".claude/skills/structural-verifier/scripts/count-comparator.py" in paths


def test_list_mode_prints_commands_without_running(capsys):
    assert check.main(["--skip-regression", "--list"]) == 0

    output = capsys.readouterr().out
    assert "pytest:" in output
    assert "python syntax:" in output
    assert "shell syntax:" in output
