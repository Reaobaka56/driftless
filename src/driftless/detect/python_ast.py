from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from driftless.discover import discover_source_files


@dataclass
class Finding:
    record_id: str
    file: str
    line: int
    symbol: str
    severity: str = "error"
    confidence: float = 0.9

    def to_dict(self):
        return asdict(self)


def dotted(node) -> str:
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        left = dotted(node.value)
        return f"{left}.{node.attr.value}" if left else ""
    return ""


def call_matches(node: cst.Call, symbol: str, param: str | None) -> bool:
    name = dotted(node.func)
    if not (name == symbol or name.endswith("." + symbol)):
        return False
    if param:
        return any(a.keyword is not None and a.keyword.value == param for a in node.args)
    return True


class _Imports(cst.CSTVisitor):
    def __init__(self, module: str):
        self.module, self.found = module, False

    def _hit(self, name: str) -> bool:
        return name == self.module or name.startswith(self.module + ".")

    def visit_Import(self, node: cst.Import):
        if any(self._hit(dotted(a.name)) for a in node.names):
            self.found = True

    def visit_ImportFrom(self, node: cst.ImportFrom):
        if node.module is not None and self._hit(dotted(node.module)):
            self.found = True


def imports_module(tree: cst.Module, module: str | None) -> bool:
    """True when no module gate is configured, or the file imports it."""
    if not module:
        return True
    v = _Imports(module)
    tree.visit(v)
    return v.found


class _Visitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, records, file):
        self.records, self.file, self.findings = records, file, []

    def visit_Call(self, node: cst.Call):
        for r in self.records:
            if call_matches(node, r.affects["symbol"], r.affects.get("param")):
                pos = self.get_metadata(PositionProvider, node).start
                self.findings.append(Finding(r.id, self.file, pos.line, r.affects["symbol"]))


def iter_py_files(repo_path: str):
    root = Path(repo_path).resolve()
    for rel in discover_source_files(root, (".py",)).files:
        yield root / rel


def scan_python_repo(repo_path: str, records: list) -> list[Finding]:
    root = Path(repo_path).resolve()
    findings: list[Finding] = []
    for py in iter_py_files(repo_path):
        try:
            module = cst.parse_module(py.read_text(encoding="utf-8"))
        except (cst.ParserSyntaxError, UnicodeDecodeError, OSError, RecursionError):  # skip unparseable files
            continue
        applicable = [r for r in records if imports_module(module, r.affects.get("module"))]
        if not applicable:
            continue
        v = _Visitor(applicable, py.relative_to(root).as_posix())
        MetadataWrapper(module).visit(v)
        findings.extend(v.findings)
    return findings
