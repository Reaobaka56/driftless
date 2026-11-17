from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import yaml
from pydantic import BaseModel, Field


class ChangeRecord(BaseModel):
    id: str
    vendor: str
    type: str
    affects: dict
    effective: str
    source_url: str
    recipe: str | None = None
    migration_note: str
    review: dict
    stats: dict = Field(default_factory=lambda: {"attempts": 0, "merged_unedited": 0})


def _yaml_files(path: str):
    return sorted(p for p in Path(path).rglob("*.yaml") if "_schema" not in p.parts)


def load_records(path: str = "registry", vendor: str | None = None,
                 record_id: str | None = None, reviewed_only: bool = True) -> list[ChangeRecord]:
    out = []
    for f in _yaml_files(path):
        data = yaml.safe_load(f.read_text())
        if vendor and data.get("vendor") != vendor:
            continue
        if record_id and data.get("id") != record_id:
            continue
        rec = ChangeRecord(**data)
        if reviewed_only and rec.review.get("status") != "reviewed":
            continue
        out.append(rec)
    return out


def validate_records(path: str = "registry") -> dict:
    schema_file = Path(path) / "_schema" / "record.schema.json"
    if not schema_file.exists():
        return {"valid": [], "errors": [("schema", "record.schema.json not found")]}
    schema = json.loads(schema_file.read_text())
    valid, errors = [], []
    for f in _yaml_files(path):
        try:
            jsonschema.validate(yaml.safe_load(f.read_text()), schema)
            valid.append(str(f))
        except Exception as e:  # noqa: BLE001
            errors.append((str(f), str(e).splitlines()[0]))
    return {"valid": valid, "errors": errors}
