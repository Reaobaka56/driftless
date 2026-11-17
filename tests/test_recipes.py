import os
import shutil
import stat

import pytest
from conftest import FIXTURES, REGISTRY

from driftless.fix.pipeline import fix_and_verify
from driftless.fix.recipes import (
    RecipeError,
    RenameKeywordParams,
    apply_rename_keyword,
    apply_to_file,
)
from driftless.registry.loader import load_records

P = RenameKeywordParams(symbol="Charge.create", param="source",
                        replacement_param="payment_method", module="stripe")
RID = "stripe-2026-11-17-charge-source"


def test_successful_rename_changes_only_the_keyword():
    src = "import stripe\n\n# charge\nstripe.Charge.create(amount=1,  source=tok,  currency='usd')  # keep\n"
    r = apply_rename_keyword(src, P)
    assert r.status == "changed" and r.replaced == 1
    assert r.new_source == src.replace("source=tok", "payment_method=tok")


def test_missing_keyword_is_unchanged():
    r = apply_rename_keyword("import stripe\nstripe.Charge.create(amount=1)\n", P)
    assert r.status == "unchanged" and r.matches == 0 and r.new_source is None


def test_invalid_python_returns_error_without_output():
    r = apply_rename_keyword("import stripe\nstripe.Charge.create(source=", P)
    assert r.status == "error" and r.new_source is None


def test_multiple_matches_all_replaced_deterministically_and_idempotent():
    src = "import stripe\n" + "".join(f"stripe.Charge.create(source=t{i})\n" for i in range(3))
    r1 = apply_rename_keyword(src, P)
    assert r1.replaced == 3 and r1.new_source == apply_rename_keyword(src, P).new_source
    assert apply_rename_keyword(r1.new_source, P).status == "unchanged"


def test_ambiguous_call_is_refused_and_left_untouched():
    src = "import stripe\nstripe.Charge.create(source=a, payment_method=b)\n"
    r = apply_rename_keyword(src, P)
    assert r.status == "refused" and r.new_source is None and r.skipped


def test_mixed_file_changes_safe_call_only():
    src = ("import stripe\nstripe.Charge.create(source=a)\n"
           "stripe.Charge.create(source=a, payment_method=b)\n")
    r = apply_rename_keyword(src, P)
    assert r.status == "changed" and r.replaced == 1 and len(r.skipped) == 1
    assert "payment_method=a" in r.new_source and "source=a, payment_method=b" in r.new_source


def test_other_library_with_same_symbol_is_not_touched():
    r = apply_rename_keyword("import acme\nacme.Charge.create(source=1)\n", P)
    assert r.status == "unchanged" and r.new_source is None


@pytest.mark.parametrize("kw", [
    dict(param="class"), dict(replacement_param="1bad"), dict(symbol="a..b"),
    dict(symbol="Charge.create; os.system"), dict(replacement_param="source")])
def test_invalid_params_rejected(kw):
    base = dict(symbol="Charge.create", param="source", replacement_param="payment_method")
    base.update(kw)
    with pytest.raises(ValueError):
        RenameKeywordParams(**base)


def test_from_record_validates_recipe_and_fields():
    rec = load_records(REGISTRY, record_id=RID)[0]
    assert RenameKeywordParams.from_record(rec).replacement_param == "payment_method"
    bad = rec.model_copy(update={"recipe": "other"})
    with pytest.raises(RecipeError):
        RenameKeywordParams.from_record(bad)
    bad = rec.model_copy(update={"affects": {"symbol": "Charge.create"}})
    with pytest.raises(RecipeError):
        RenameKeywordParams.from_record(bad)


def test_apply_to_file_invalid_targets(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "notes.txt").write_text("import stripe")
    outside = tmp_path / "outside.py"
    outside.write_text("import stripe\nstripe.Charge.create(source=1)\n")
    os.symlink(outside, root / "link.py")
    assert apply_to_file(root / "missing.py", root, P).status == "error"
    assert apply_to_file(root / "notes.txt", root, P).status == "error"
    assert apply_to_file(root / "link.py", root, P).status == "error"   # symlink refused
    assert apply_to_file(outside, root, P).status == "error"            # outside repo
    assert "source=1" in outside.read_text()


def test_apply_to_file_writes_atomically_keeps_mode_and_dry_run_is_pure(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("import stripe\nstripe.Charge.create(source=1)\n")
    f.chmod(0o751)
    assert apply_to_file(f, tmp_path, P, dry_run=True).status == "changed"
    assert "source=1" in f.read_text()
    assert apply_to_file(f, tmp_path, P).status == "changed"
    assert "payment_method=1" in f.read_text() and stat.S_IMODE(f.stat().st_mode) == 0o751
    assert [p.name for p in tmp_path.iterdir()] == ["a.py"]             # no temp files left


def test_fix_pipeline_with_ambiguous_call_is_draft_and_leaves_it(tmp_path):
    repo = tmp_path / "r"
    shutil.copytree(FIXTURES / "sample_repo", repo)
    (repo / "amb.py").write_text("import stripe\nstripe.Charge.create(source=a, payment_method=b)\n")
    r = fix_and_verify(RID, str(repo), registry=REGISTRY)
    assert r.status == "draft" and r.changed_files == ["app.py"] and r.skipped
    assert (repo / "amb.py").read_text().endswith("source=a, payment_method=b)\n")
    assert "payment_method=token" in (repo / "app.py").read_text()


def test_fix_pipeline_unknown_record_fails_cleanly(tmp_path):
    assert fix_and_verify("nope", str(tmp_path), registry=REGISTRY).status == "failed"
