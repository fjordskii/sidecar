#!/usr/bin/env python3
"""
schema_check.py — a small, dependency-free validator for the subset of JSON Schema
`schema/state.schema.json` actually uses.

Why not `jsonschema`: for the same reason the engine imports nothing but the standard
library — a clone must run from a bare `git clone`, or the promise that "the exact engine
that produced any historical cycle is recoverable from that commit" is false the day a
runner has a different pip environment, inside somebody's 09:30 cycle that nobody is
watching. If `jsonschema` IS installed we defer to it, so the strict library is what runs
in CI.

Supported: $ref (local), definitions, type (incl. unions), required, properties,
additionalProperties (schema or bool), items, enum, minimum, and `"not": {}` (meaning
"this key must not be present at all").
"""

from __future__ import annotations

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def validate(instance, schema: dict) -> list[str]:
    """-> list of human-readable errors. Empty list means valid."""
    try:
        import jsonschema  # optional — the strict library if present, our subset if not
    except Exception:
        return _validate(instance, schema, schema, "$")
    v = jsonschema.Draft7Validator(schema)
    return [f"{'.'.join(str(p) for p in e.path) or '$'}: {e.message}"
            for e in sorted(v.iter_errors(instance), key=lambda e: list(e.path))]


def _resolve(schema: dict, root: dict) -> dict:
    ref = schema.get("$ref")
    if not ref:
        return schema
    if not ref.startswith("#/"):
        return {}
    node = root
    for part in ref[2:].split("/"):
        node = node.get(part, {})
    return node


def _type_ok(value, t) -> bool:
    if isinstance(t, list):
        return any(_type_ok(value, x) for x in t)
    py = _TYPES.get(t)
    if py is None:
        return True
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "boolean":
        return isinstance(value, bool)
    return isinstance(value, py)


def _validate(value, schema: dict, root: dict, path: str) -> list[str]:
    errs: list[str] = []
    schema = _resolve(schema, root)
    if not schema:
        return errs

    if "type" in schema and not _type_ok(value, schema["type"]):
        return [f"{path}: expected {schema['type']}, got {type(value).__name__}"]

    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: {value!r} is not one of {schema['enum']}")

    if "minimum" in schema and isinstance(value, (int, float)) and not isinstance(value, bool):
        if value < schema["minimum"]:
            errs.append(f"{path}: {value} < minimum {schema['minimum']}")

    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errs.append(f"{path}: missing required key '{req}'")
        props = schema.get("properties", {})
        for k, sub in props.items():
            sub = _resolve(sub, root)
            if sub.get("not") == {}:
                if k in value:
                    errs.append(f"{path}.{k}: must not be present ({sub.get('description', '')})".rstrip(" ()"))
                continue
            if k in value:
                errs += _validate(value[k], sub, root, f"{path}.{k}")
        addl = schema.get("additionalProperties")
        if isinstance(addl, dict):
            for k, v in value.items():
                if k not in props:
                    errs += _validate(v, addl, root, f"{path}.{k}")
        elif addl is False:
            for k in value:
                if k not in props:
                    errs.append(f"{path}.{k}: additional properties are not allowed")

    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for i, item in enumerate(value):
            errs += _validate(item, schema["items"], root, f"{path}[{i}]")

    return errs
