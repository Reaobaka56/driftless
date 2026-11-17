"""Source file discovery: honours .gitignore, skips deps/build output/symlinks."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import pathspec

DEFAULT_EXCLUDED_DIRS = frozenset({
    ".git", "node_modules", "dist", "build", "out", ".next", ".nuxt", "coverage",
    ".turbo", ".cache", "vendor", "__pycache__", ".venv", "venv", ".tox",
    ".mypy_cache", ".pytest_cache",
})
TS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")
GENERATED_SUFFIXES = (".d.ts", ".min.js", ".bundle.js")


@dataclass
class Discovery:
    files: list[str] = field(default_factory=list)  # repo-relative, "/" separated
    skipped: list[dict] = field(default_factory=list)


def _load_spec(directory: Path) -> pathspec.GitIgnoreSpec | None:
    gi = directory / ".gitignore"
    if gi.is_file() and not gi.is_symlink():
        try:
            return pathspec.GitIgnoreSpec.from_lines(
                gi.read_text(errors="replace").splitlines())
        except OSError:
            return None
    return None


def discover_source_files(
    root: str | Path,
    extensions: tuple[str, ...] = TS_EXTENSIONS,
    *,
    max_file_bytes: int = 1_000_000,
    excluded_dirs: frozenset[str] = DEFAULT_EXCLUDED_DIRS,
) -> Discovery:
    root = Path(root).resolve()
    out = Discovery()
    specs: dict[str, pathspec.GitIgnoreSpec] = {}

    def ignored(rel: str, is_dir: bool) -> bool:
        for base, spec in specs.items():
            if base and not rel.startswith(base + "/"):
                continue
            sub = rel[len(base) + 1:] if base else rel
            if spec.match_file(sub + "/" if is_dir else sub):
                return True
        return False

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        d = Path(dirpath)
        rel_dir = "" if d == root else d.relative_to(root).as_posix()
        spec = _load_spec(d)
        if spec is not None:
            specs[rel_dir] = spec
        dirnames[:] = sorted(
            n for n in dirnames
            if n not in excluded_dirs
            and not (d / n).is_symlink()
            and not ignored(f"{rel_dir}/{n}".lstrip("/"), True))
        for name in sorted(filenames):
            if not name.endswith(extensions) or name.endswith(GENERATED_SUFFIXES):
                continue
            p = d / name
            rel = f"{rel_dir}/{name}".lstrip("/")
            if p.is_symlink() or ignored(rel, False):
                continue
            try:
                size = p.stat().st_size
            except OSError as e:
                out.skipped.append({"file": rel, "reason": f"stat failed: {e}"})
                continue
            if size > max_file_bytes:
                out.skipped.append({"file": rel, "reason": f"larger than {max_file_bytes} bytes"})
                continue
            out.files.append(rel)
    return out
