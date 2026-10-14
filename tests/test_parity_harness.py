"""The reusable smoke command exercises real CLI reports on isolated data."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify-parity.py"
CHECKOUT = SCRIPT.parents[1]
BASELINE = (CHECKOUT.parent / "token-cost-reporting" if CHECKOUT.parent.name == ".worktrees"
            else CHECKOUT / ".worktrees" / "token-cost-reporting")


@pytest.mark.skipif(not BASELINE.is_dir(), reason="requires the deployed baseline checkout")
def test_real_cli_parity_survives_migration_restart_and_aliases(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--baseline", str(BASELINE),
         "--work-dir", str(tmp_path), "--json", "--plain"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr.isascii()
    data = json.loads(result.stdout)
    assert data["passed"]
    assert set(data["reports"]) >= {
        "history", "sessions", "model-time", "allowance", "overview", "projects",
    }
    assert all(data["reports"].values())
    assert data["aliases"] == {
        "burn": True, "models": True, "day": True,
        "list": True, "report": True, "status": True,
    }
    assert data["migration"]["backup_verified"]
    assert data["restart"]["reports_unchanged"]
    assert data["native"]["projection_equal"]
    assert data["assertions"]["precise_wait_subtraction"]
    assert data["assertions"]["child_excluded"]
    assert data["assertions"]["exact_large_counter"]
    assert "check_age_seconds" in data["normalized_clock_fields"]


def test_missing_checkout_reports_machine_error_and_leaves_no_fixture(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--baseline", str(tmp_path / "missing"),
         "--work-dir", str(tmp_path / "work"), "--json", "--plain"],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert not data["passed"]
    assert "baseline" in data["error"]
    assert not (tmp_path / "work").exists()


@pytest.mark.skipif(not BASELINE.is_dir(), reason="requires the deployed baseline checkout")
def test_supplied_fixture_is_read_only_and_has_explicit_coverage_gap(tmp_path: Path) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("parity_harness", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fixture = tmp_path / "supplied"
    module.generate_fixture(fixture)
    (fixture / "home" / "auth.json").write_text('{"token":"PRIVATE_FIXTURE_CREDENTIAL"}')
    before = {str(path.relative_to(fixture)): path.read_bytes()
              for path in fixture.rglob("*") if path.is_file()}
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--baseline", str(BASELINE),
         "--fixture", str(fixture), "--work-dir", str(tmp_path / "run"),
         "--json", "--plain"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["passed"]
    assert any("supplied fixture" in gap.lower() for gap in data["gaps"])
    assert not (tmp_path / "run" / "baseline" / "home" / "auth.json").exists()
    assert not (tmp_path / "run" / "optimized" / "home" / "auth.json").exists()
    assert before == {str(path.relative_to(fixture)): path.read_bytes()
                      for path in fixture.rglob("*") if path.is_file()}


def test_native_reader_uses_supplied_projection_dates(tmp_path: Path) -> None:
    import importlib.util
    import shutil

    if shutil.which("timetrace") is None:
        pytest.skip("native reader is not installed")
    if any(Path("/etc/timetrace", name).exists() for name in ("config.yml", "config.yaml")):
        pytest.skip("system configuration prevents isolated native reads")
    spec = importlib.util.spec_from_file_location("parity_native", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("baseline", "optimized"):
        data = tmp_path / name / "data"
        module.dump(data / "projects" / "fixture.json", {"key": "fixture", "name": "/fixture"})
        module.dump(data / "records" / "2027-01-01" / "codex-time-fixture.json", {
            "start": "2027-01-01T12:00:00+00:00", "end": "2027-01-01T12:00:01+00:00",
            "project": {"key": "fixture"}, "is_billable": False, "tags": ["session:outside"],
        })
    result = module.native_reader(
        module.Runner(True), tmp_path / "baseline", tmp_path / "optimized"
    )
    assert result["status"] == "passed"
    assert result["reported_nanoseconds"] == 1_000_000_000
    assert result["date_range"] == {"from": "2027-01-01", "to": "2027-01-01"}
