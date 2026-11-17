"""Recipes: pure, deterministic source transformations with structured results."""
from __future__ import annotations

import keyword
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import libcst as cst
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from driftless.detect.python_ast import call_matches, imports_module

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class RecipeError(ValueError):
    """Invalid recipe inputs. Raised before any file is touched."""


class RenameKeywordParams(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: str
    param: str
    replacement_param: str
    module: str | None = None

    @field_validator("symbol")
    @classmethod
    def _symbol(cls, v: str) -> str:
        if not all(_IDENT.match(p) and not keyword.iskeyword(p) for p in v.split(".")):
            raise ValueError(f"invalid dotted symbol {v!r}")
        return v

    @field_validator("param", "replacement_param")
    @classmethod
    def _ident(cls, v: str) -> str:
        if not _IDENT.match(v) or keyword.iskeyword(v):
            raise ValueError(f"invalid keyword name {v!r}")
        return v

    @model_validator(mode="after")
    def _distinct(self):
        if self.param == self.replacement_param:
            raise ValueError("param and replacement_param must differ")
        return self

    @classmethod
    def from_record(cls, record) -> RenameKeywordParams:
        if record.recipe != "rename_keyword":
            raise RecipeError(f"record {record.id} does not use the rename_keyword recipe")
        a = record.affects
        try:
            return cls(symbol=a.get("symbol"), param=a.get("param"),
                       replacement_param=a.get("replacement_param"), module=a.get("module"))
        except ValueError as e:
            raise RecipeError(f"invalid recipe inputs for {record.id}: {e}") from e


@dataclass
class RecipeResult:
    status: str  # changed | unchanged | refused | error
    new_source: str | None = None
    matches: int = 0
    replaced: int = 0
    skipped: list[str] = field(default_factory=list)  # "line N: reason"
    error: str | None = None


class _Rename(cst.CSTTransformer):
    METADATA_DEPENDENCIES = ()

    def __init__(self, p: RenameKeywordParams):
        self.p, self.matches, self.replaced = p, 0, 0
        self.skipped: list[str] = []

    def leave_Call(self, original_node, updated_node):
        if not call_matches(original_node, self.p.symbol, self.p.param):
            return updated_node
        self.matches += 1
        kws = [a.keyword.value for a in updated_node.args if a.keyword is not None]
        if self.p.replacement_param in kws:
            self.skipped.append(f"{self.p.symbol}: both '{self.p.param}' and "
                                f"'{self.p.replacement_param}' passed (ambiguous)")
            return updated_node
        if kws.count(self.p.param) != 1:
            self.skipped.append(f"{self.p.symbol}: '{self.p.param}' passed more than once")
            return updated_node
        self.replaced += 1
        args = [a.with_changes(keyword=a.keyword.with_changes(value=self.p.replacement_param))
                if a.keyword is not None and a.keyword.value == self.p.param else a
                for a in updated_node.args]
        return updated_node.with_changes(args=args)


def apply_rename_keyword(source: str, p: RenameKeywordParams) -> RecipeResult:
    try:
        tree = cst.parse_module(source)
    except cst.ParserSyntaxError as e:
        return RecipeResult("error", error=f"syntax error: {e.message}")
    if not imports_module(tree, p.module):
        return RecipeResult("unchanged", skipped=[f"file does not import '{p.module}'"])
    t = _Rename(p)
    new = tree.visit(t)
    res = RecipeResult("unchanged", matches=t.matches, replaced=t.replaced, skipped=t.skipped)
    if t.replaced:
        res.status, res.new_source = "changed", new.code
    elif t.matches:
        res.status = "refused"
    return res


def apply_to_file(path: Path, root: Path, p: RenameKeywordParams, *, dry_run: bool = False) -> RecipeResult:
    """Validate the target, apply the recipe, write atomically (unless dry_run)."""
    root = root.resolve()
    if path.is_symlink():
        return RecipeResult("error", error="refusing to modify a symlink")
    try:
        real = path.resolve(strict=True)
        real.relative_to(root)
    except (OSError, ValueError):
        return RecipeResult("error", error="target is missing or outside the repository")
    if not real.is_file() or real.suffix != ".py":
        return RecipeResult("error", error="target is not a .py file")
    try:
        source = real.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return RecipeResult("error", error=f"cannot read file: {e}")
    res = apply_rename_keyword(source, p)
    if res.status == "changed" and not dry_run:
        fd, tmp = tempfile.mkstemp(dir=real.parent, prefix=".driftless-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
                fh.write(res.new_source or "")
            shutil.copymode(real, tmp)
            os.replace(tmp, real)
        except OSError as e:
            Path(tmp).unlink(missing_ok=True)
            return RecipeResult("error", error=f"write failed: {e}")
    return res
