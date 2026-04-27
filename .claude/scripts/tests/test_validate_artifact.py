import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validate_artifact import validate


def test_valid_object_passes():
    schema = {
        "type": "object",
        "required": ["status"],
        "properties": {"status": {"type": "string", "enum": ["PASS", "FAIL"]}},
        "additionalProperties": False,
    }
    assert validate({"status": "PASS"}, schema) == []


def test_missing_required_fails():
    schema = {"type": "object", "required": ["status"], "properties": {}}
    assert "missing required property 'status'" in validate({}, schema)[0]


def test_nested_array_items_are_validated():
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {"type": "object", "required": ["id"], "properties": {"id": {"type": "string"}}},
            }
        },
    }
    assert validate({"items": [{"id": 1}]}, schema) == ["$.items[0].id: expected string, got int"]
