#!/usr/bin/env python3
"""Small JSON artifact validator for pipeline sidecars.

The project may later switch to the jsonschema package. Until dependency
management is formalized, this validator supports the schema subset used by
the repo: type, required, properties, items, enum, additionalProperties, and
minItems.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class ValidationError(ValueError):
    """Raised when artifact data does not satisfy the schema."""


TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, TYPE_MAP[expected])


def validate(data: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []

    expected_type = schema.get("type")
    if isinstance(expected_type, list):
        if not any(_type_matches(data, item) for item in expected_type):
            errors.append(f"{path}: expected one of {expected_type}, got {type(data).__name__}")
            return errors
    elif expected_type:
        if expected_type not in TYPE_MAP:
            errors.append(f"{path}: unsupported schema type {expected_type!r}")
            return errors
        if not _type_matches(data, expected_type):
            errors.append(f"{path}: expected {expected_type}, got {type(data).__name__}")
            return errors

    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{path}: expected one of {schema['enum']!r}, got {data!r}")

    if isinstance(data, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in data:
                errors.append(f"{path}: missing required property {key!r}")

        properties = schema.get("properties", {})
        for key, value in data.items():
            if key in properties:
                errors.extend(validate(value, properties[key], f"{path}.{key}"))
            elif schema.get("additionalProperties", True) is False:
                errors.append(f"{path}: unexpected property {key!r}")

    if isinstance(data, list):
        min_items = schema.get("minItems")
        if min_items is not None and len(data) < min_items:
            errors.append(f"{path}: expected at least {min_items} item(s), got {len(data)}")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(data):
                errors.extend(validate(item, item_schema, f"{path}[{index}]"))

    return errors


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate a JSON artifact against a repo schema.")
    parser.add_argument("--schema", required=True, help="Path to schema JSON")
    parser.add_argument("--file", required=True, help="Path to artifact JSON")
    args = parser.parse_args(argv)

    try:
        schema = load_json(Path(args.schema))
        data = load_json(Path(args.file))
    except json.JSONDecodeError as exc:
        print(f"validate-artifact: invalid JSON: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"validate-artifact: {exc}", file=sys.stderr)
        return 2

    errors = validate(data, schema)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"PASS: {args.file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
