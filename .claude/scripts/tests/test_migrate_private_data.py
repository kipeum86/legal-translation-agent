import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "migrate-private-data.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("migrate_private_data", SCRIPT)
migrate_private_data = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(migrate_private_data)


def test_discover_skips_public_library_example(tmp_path):
    root = tmp_path / "repo"
    private = tmp_path / "private"
    (root / "library" / "_example").mkdir(parents=True)
    (root / "library" / "_example" / "profile.json").write_text("{}", encoding="utf-8")
    (root / "library" / ".gitkeep").write_text("", encoding="utf-8")
    (root / "library" / "acme").mkdir()
    (root / "library" / "acme" / "style.md").write_text("style", encoding="utf-8")

    moves = migrate_private_data.discover(root, private)

    assert [move["name"] for move in moves] == ["library/acme"]
    assert moves[0]["target"] == private / "library" / "acme"


def test_apply_moves_writes_verified_target_inventory(tmp_path):
    root = tmp_path / "repo"
    private = tmp_path / "private"
    (root / "input").mkdir(parents=True)
    (root / "input" / "source.md").write_text("source", encoding="utf-8")
    (root / "config.json").write_text('{"ok":true}', encoding="utf-8")
    (root / "library" / "_example").mkdir(parents=True)
    (root / "library" / "_example" / "profile.json").write_text("{}", encoding="utf-8")
    (root / "library" / "acme").mkdir()
    (root / "library" / "acme" / "terms.json").write_text("{}", encoding="utf-8")

    moves = migrate_private_data.discover(root, private)
    errors = migrate_private_data.apply_moves(moves)
    manifest_path = migrate_private_data.write_manifest(private, moves, applied=True)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert errors == []
    assert (private / "input" / "source.md").exists()
    assert (private / "config.json").exists()
    assert (private / "library" / "acme" / "terms.json").exists()
    assert (root / "library" / "_example" / "profile.json").exists()
    assert all(move["verified"] is True for move in payload["moves"])
    assert all(move["target_inventory"] is not None for move in payload["moves"])


def test_apply_moves_refuses_existing_target_before_moving(tmp_path):
    root = tmp_path / "repo"
    private = tmp_path / "private"
    (root / "input").mkdir(parents=True)
    (root / "input" / "source.md").write_text("source", encoding="utf-8")
    (private / "input").mkdir(parents=True)

    moves = migrate_private_data.discover(root, private)

    with pytest.raises(RuntimeError):
        migrate_private_data.apply_moves(moves)
    assert (root / "input" / "source.md").exists()
