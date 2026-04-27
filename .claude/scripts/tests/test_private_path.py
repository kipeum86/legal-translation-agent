import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from private_path import PathPolicyError, repo_root, resolve_private_path


def test_managed_relative_path_uses_private_root(tmp_path):
    env = {"LEGAL_TRANSLATION_PRIVATE_DIR": str(tmp_path)}
    assert resolve_private_path("input/source.md", env=env) == tmp_path / "input/source.md"


def test_managed_relative_path_requires_env():
    with pytest.raises(PathPolicyError):
        resolve_private_path("output/working", env={})


def test_public_library_example_stays_in_repo(tmp_path):
    env = {"LEGAL_TRANSLATION_PRIVATE_DIR": str(tmp_path)}
    expected = repo_root() / "library" / "_example" / "profile.json"
    assert resolve_private_path("library/_example/profile.json", env=env) == expected.resolve()


def test_absolute_repo_private_path_is_rejected(tmp_path):
    env = {"LEGAL_TRANSLATION_PRIVATE_DIR": str(tmp_path)}
    bad_path = repo_root() / "output" / "working"
    with pytest.raises(PathPolicyError):
        resolve_private_path(str(bad_path), env=env)
