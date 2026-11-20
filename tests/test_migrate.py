from pathlib import Path

from worker.migrate import MIGRATIONS_DIR, list_migrations


def test_down_migrations_are_never_applied(tmp_path: Path):
    names = ["001_init.sql", "001_down.sql", "002_scan_analysis.sql", "002_down.sql", "notes.txt"]
    names.append("10_later.sql")
    for name in names:
        (tmp_path / name).write_text("SELECT 1;")
    found = [p.name for p in list_migrations(tmp_path)]
    assert found == ["001_init.sql", "002_scan_analysis.sql", "10_later.sql"]


def test_real_migrations_are_ordered_and_exclude_down():
    names = [p.name for p in list_migrations(MIGRATIONS_DIR)]
    assert names == sorted(names)
    assert names[:2] == ["001_init.sql", "002_scan_analysis.sql"]
    assert not any("down" in n for n in names)
