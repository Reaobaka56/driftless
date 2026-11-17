import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
REGISTRY = str(ROOT / "registry")


def _ts_available() -> bool:
    node = shutil.which("node")
    if not node:
        return False
    script = ROOT / "src/driftless/scanners/ts/scan.mjs"
    p = subprocess.run([node, str(script)], check=False, input='{"root":".","files":[]}',
                       capture_output=True, text=True, cwd=script.parent)
    return p.returncode == 0


requires_ts = pytest.mark.skipif(
    not _ts_available(), reason="node + typescript not installed (npm install in scanners/ts)")


@pytest.fixture(autouse=True)
def _no_real_llm_keys(monkeypatch):
    for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DRIFTLESS_NODE"):
        monkeypatch.delenv(k, raising=False)


@pytest.fixture
def ts_repo(tmp_path):
    dest = tmp_path / "ts_repo"
    shutil.copytree(FIXTURES / "ts_repo", dest)
    # "trap" directories are created at test time: git would drop them from the fixtures
    for d, name in (("node_modules/dep", "index.js"), ("dist", "out.js"), ("generated", "gen.ts")):
        (dest / d).mkdir(parents=True)
        (dest / d / name).write_text("eval(process.argv[2]);\n")
    return dest
