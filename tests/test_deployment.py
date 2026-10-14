"""Operator CLI refuses incomplete or modified deployment artifacts."""

import hashlib
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "deployment.py"


def write_manifest(bundle: Path, manifest: dict[str, object]) -> None:
    path = bundle / "manifest.json"
    path.write_text(json.dumps(manifest))
    (bundle / "manifest.sha256").write_text(hashlib.sha256(path.read_bytes()).hexdigest())


def command(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--plain", "--json", *arguments],
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_verify_detects_modified_artifact(tmp_path: Path) -> None:
    wheel = tmp_path / "new.whl"
    wheel.write_bytes(b"known wheel bytes")
    write_manifest(
        tmp_path,
        {
            "version": 1,
            "artifacts": {"new.whl": hashlib.sha256(wheel.read_bytes()).hexdigest()},
        },
    )
    result = command("verify", "--bundle", str(tmp_path))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["verified"] is True
    wheel.write_bytes(b"modified wheel")
    refused = command("verify", "--bundle", str(tmp_path))
    assert refused.returncode == 1
    assert "hash" in refused.stderr.lower()
    assert not refused.stdout


def operator_bundle(tmp_path: Path, *, recovery_failure: bool = False) -> tuple[Path, Path]:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    data = tmp_path / "data"
    data.mkdir()
    (data / "ledger.json").write_text('{"version":4,"sessions":{}}')
    (data / "auth.json").write_text("never copy this unrelated file")
    state = tmp_path / "state"
    state.mkdir()
    (state / "checkpoint.json").write_text("{}")
    (state / "unrelated.txt").write_text("preserve me")
    events = tmp_path / "events.jsonl"
    unit_text = f'[Service]\nExecStart="{tmp_path}/codex-time" daemon\n'
    systemctl = tmp_path / "systemctl"
    systemctl.write_text(
        f"#!{sys.executable}\n"
        "import json,sys\n"
        f"with open({str(events)!r}, 'a') as f:f.write(json.dumps(sys.argv[1:])+'\\n')\n"
        f"if 'cat' in sys.argv:print({unit_text!r},end='')\n"
    )
    systemctl.chmod(0o755)
    uv = tmp_path / "uv"
    uv.write_text(
        f"#!{sys.executable}\n"
        "import json,sys\n"
        f"with open({str(events)!r}, 'a') as f:f.write(json.dumps(sys.argv[1:])+'\\n')\n"
    )
    uv.chmod(0o755)
    executable = tmp_path / "codex-time"
    executable.write_text("previous installed executable")
    recovery = bundle / "recover.py"
    recovery.write_text(
        "import json,sys\n"
        + (
            "raise SystemExit('intentional recovery refusal')\n"
            if recovery_failure
            else f"sys.path.insert(0,{str(SCRIPT.parent.parent / 'src')!r})\n"
            f"exec(compile(open({str(SCRIPT.parent / 'storage-recovery.py')!r}).read(),"
            "'storage-recovery.py','exec'))\n"
        )
    )
    for name in ("new.whl", "previous.whl"):
        (bundle / name).write_bytes(b"wheel")
    (bundle / "unit.txt").write_text(unit_text)
    artifacts = {
        name: hashlib.sha256((bundle / name).read_bytes()).hexdigest()
        for name in ("new.whl", "previous.whl", "recover.py", "unit.txt")
    }
    write_manifest(
        bundle,
        {
            "version": 1,
            "artifacts": artifacts,
            "new_wheel": "new.whl",
            "previous_wheel": "previous.whl",
            "recovery_python": sys.executable,
            "recovery_script": "recover.py",
            "systemctl": str(systemctl),
            "uv": str(uv),
            "service": "codex-time.service",
            "unit_text": "unit.txt",
            "unit_argv": [str(tmp_path / "codex-time"), "daemon"],
            "dropin": str(tmp_path / "codex-time.service.d" / "90-codex-time-deployment.conf"),
            "data_dir": str(data),
            "state_dir": str(state),
            "python": sys.executable,
            "installed_files": {
                str(executable): hashlib.sha256(executable.read_bytes()).hexdigest(),
            },
            "new_installed_files": {
                str(executable): hashlib.sha256(executable.read_bytes()).hexdigest(),
            },
            "lock": str(tmp_path / "writer.lock"),
        },
    )
    return bundle, events


def test_failed_backup_refuses_install_and_preserves_source(tmp_path: Path) -> None:
    bundle, events = operator_bundle(tmp_path, recovery_failure=True)
    before = (tmp_path / "data" / "ledger.json").read_bytes()
    result = command("activate", "--bundle", str(bundle))
    assert result.returncode == 1
    assert "recovery refusal" in result.stderr
    operations = [json.loads(line) for line in events.read_text().splitlines()]
    assert ["--user", "stop", "codex-time.service"] in operations
    assert ["--user", "start", "codex-time.service"] in operations
    assert not any("install" in operation for operation in operations)
    assert (tmp_path / "data" / "ledger.json").read_bytes() == before
    assert not (bundle / "activation.json").exists()


def test_activation_has_verified_content_free_backup_before_install(tmp_path: Path) -> None:
    bundle, events = operator_bundle(tmp_path)
    result = command("activate", "--bundle", str(bundle))
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["stage"] == "active"
    backup = Path(report["backup"]["path"])
    assert report["backup"]["verified"] is True
    assert (backup / "data" / "ledger.json").read_bytes() == (
        tmp_path / "data" / "ledger.json"
    ).read_bytes()
    assert not (backup / "data" / "auth.json").exists()
    assert not (backup / "runtime" / "unrelated.txt").exists()
    operations = [json.loads(line) for line in events.read_text().splitlines()]
    assert any("install" in operation for operation in operations)
    assert operations[-1] == ["--user", "start", "codex-time.service"]


def test_rollback_exports_current_evidence_without_replacing_source(tmp_path: Path) -> None:
    bundle, events = operator_bundle(tmp_path)
    activated = command("activate", "--bundle", str(bundle))
    assert activated.returncode == 0, activated.stderr
    ledger = tmp_path / "data" / "ledger.json"
    ledger.write_text(
        json.dumps(
            {
                "version": 4,
                "sessions": {
                    "new-session": {
                        "id": "new-session",
                        "cwd": "/sanitized",
                        "created": "2026-10-14T12:00:00Z",
                        "updated": "2026-10-14T12:01:00Z",
                        "turns": {
                            "new-turn": {
                                "id": "new-turn",
                                "cwd": "/sanitized",
                                "start": "2026-10-14T12:00:00.125Z",
                                "end": "2026-10-14T12:01:00.250Z",
                            }
                        },
                    }
                },
            }
        )
    )
    before = ledger.read_bytes()
    result = command("rollback", "--bundle", str(bundle))
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["stage"] == "rolled-back"
    assert ledger.read_bytes() == before
    assert (tmp_path / "data" / "auth.json").read_text() == "never copy this unrelated file"
    assert (tmp_path / "state" / "unrelated.txt").read_text() == "preserve me"
    exported = Path(report["export"])
    current_turn = json.loads((exported / "ledger.json").read_bytes())["sessions"]["new-session"][
        "turns"
    ]["new-turn"]
    assert current_turn["start"] == "2026-10-14T12:00:00.125000Z"
    assert current_turn["end"] == "2026-10-14T12:01:00.250000Z"
    dropin = Path(json.loads((bundle / "manifest.json").read_bytes())["dropin"])
    assert str(exported) in dropin.read_text()
    assert str(tmp_path / "codex-time") in dropin.read_text()
    operations = [json.loads(line) for line in events.read_text().splitlines()]
    install_operations = [operation for operation in operations if "install" in operation]
    assert install_operations[-1][-1] == str(bundle / "previous.whl")


def test_prepare_refuses_existing_destination_and_missing_wheel(tmp_path: Path) -> None:
    result = command(
        "prepare",
        "--wheel",
        str(tmp_path / "missing.whl"),
        "--destination",
        str(tmp_path),
    )
    assert result.returncode == 1
    assert "wheel" in result.stderr.lower()
    assert not (tmp_path / "manifest.json").exists()


def test_artifact_corruption_refuses_activation_before_service_stop(tmp_path: Path) -> None:
    bundle, events = operator_bundle(tmp_path)
    (bundle / "new.whl").write_bytes(b"wrong package")
    result = command("activate", "--bundle", str(bundle))
    assert result.returncode == 1
    assert "hash mismatch" in result.stderr
    assert not events.exists()


def test_invalid_new_evidence_refuses_rollback_install(tmp_path: Path) -> None:
    bundle, events = operator_bundle(tmp_path)
    activated = command("activate", "--bundle", str(bundle))
    assert activated.returncode == 0, activated.stderr
    ledger = tmp_path / "data" / "ledger.json"
    ledger.write_bytes(b"corrupted but preserved newer evidence")
    before = ledger.read_bytes()
    result = command("rollback", "--bundle", str(bundle))
    assert result.returncode == 1
    operations = [json.loads(line) for line in events.read_text().splitlines()]
    assert len([operation for operation in operations if "install" in operation]) == 1
    assert ledger.read_bytes() == before
    assert not Path(json.loads((bundle / "manifest.json").read_bytes())["dropin"]).exists()


def test_rollback_refuses_unrelated_projection_files_before_export(tmp_path: Path) -> None:
    bundle, events = operator_bundle(tmp_path)
    activated = command("activate", "--bundle", str(bundle))
    assert activated.returncode == 0, activated.stderr
    projects = tmp_path / "data" / "projects"
    projects.mkdir()
    unrelated = projects / "unrelated-auth.txt"
    unrelated.write_text("synthetic unrelated content must not be copied")
    result = command("rollback", "--bundle", str(bundle))
    assert result.returncode == 1
    assert "projection" in result.stderr.lower()
    assert not list(bundle.glob("rollback-legacy-*"))
    operations = [json.loads(line) for line in events.read_text().splitlines()]
    assert len([operation for operation in operations if "install" in operation]) == 1
    assert unrelated.read_text() == "synthetic unrelated content must not be copied"


def test_rollback_preserves_verified_fx_cache_for_offline_cad_reports(tmp_path: Path) -> None:
    bundle, _ = operator_bundle(tmp_path)
    (tmp_path / "data" / "ledger.json").write_text(
        json.dumps(
            {
                "version": 4,
                "sessions": {
                    "offline-session": {
                        "id": "offline-session",
                        "cwd": "/sanitized",
                        "created": "2026-10-14T12:00:00Z",
                        "updated": "2026-10-14T12:00:00Z",
                    }
                },
            }
        )
    )
    (tmp_path / "data" / "usage-observations.jsonl").write_text(
        json.dumps(
            {
                "id": "offline-cost",
                "session_id": "offline-session",
                "at": "2026-10-14T12:00:00Z",
                "cwd": "/sanitized",
                "model_id": "gpt-6.1-sol",
                "request_input_tokens": 1000,
                "delta": {
                    "input_tokens": 1000,
                    "cached_input_tokens": 0,
                    "cache_write_input_tokens": 0,
                    "output_tokens": 0,
                    "reasoning_output_tokens": 0,
                    "total_tokens": 1000,
                },
            }
        )
        + "\n"
    )
    cache = tmp_path / "state" / "fx-usd-cad.json"
    cache.write_text('{"version":1,"rate":"1.3712","observation_date":"2026-10-13"}')
    activated = command("activate", "--bundle", str(bundle))
    assert activated.returncode == 0, activated.stderr
    expected = cache.read_bytes()
    result = command("rollback", "--bundle", str(bundle))
    assert result.returncode == 0, result.stderr
    rollback = json.loads(result.stdout)
    runtime = Path(rollback["runtime"])
    assert (runtime / "fx-usd-cad.json").read_bytes() == expected
    assert cache.read_bytes() == expected
    cli = Path(sys.executable).parent / "codex-time"
    overview = subprocess.run(
        [
            str(cli),
            "--data-dir",
            rollback["export"],
            "--state-dir",
            str(runtime),
            "overview",
            "all",
            "--plain",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    token_report = json.loads(overview.stdout)["token_usage"]
    assert token_report["fx"]["rate"] == "1.3712"
    assert Decimal(token_report["usage"]["usd"]) == Decimal("0.002")
    assert Decimal(token_report["usage"]["cad"]) == Decimal("0.0027424")
    assert (runtime / "fx-usd-cad.json").read_bytes() == expected


def test_concurrent_package_change_refuses_rollback_before_stopping(tmp_path: Path) -> None:
    bundle, events = operator_bundle(tmp_path)
    activated = command("activate", "--bundle", str(bundle))
    assert activated.returncode == 0, activated.stderr
    (tmp_path / "codex-time").write_text("another separately installed package")
    result = command("rollback", "--bundle", str(bundle))
    assert result.returncode == 1
    assert "package changed" in result.stderr
    operations = [json.loads(line) for line in events.read_text().splitlines()]
    assert len([operation for operation in operations if "stop" in operation]) == 1
    assert len([operation for operation in operations if "install" in operation]) == 1


def test_package_changed_during_backup_refuses_install(tmp_path: Path) -> None:
    bundle, events = operator_bundle(tmp_path)
    recovery = bundle / "recover.py"
    recovery.write_text(
        "import sys\nfrom pathlib import Path\n"
        f"sys.path.insert(0,{str(SCRIPT.parent.parent / 'src')!r})\n"
        "scope={'__name__':'recovery_under_test'}\n"
        f"exec(compile(open({str(SCRIPT.parent / 'storage-recovery.py')!r}).read(),"
        "'storage-recovery.py','exec'),scope)\n"
        "code=scope['main']()\n"
        "if 'pre-activation-' in sys.argv[sys.argv.index('--data-dir')+1]:\n"
        f"    Path({str(tmp_path / 'codex-time')!r}).write_text('changed during backup')\n"
        "raise SystemExit(code)\n"
    )
    manifest = json.loads((bundle / "manifest.json").read_bytes())
    manifest["artifacts"]["recover.py"] = hashlib.sha256(recovery.read_bytes()).hexdigest()
    write_manifest(bundle, manifest)
    result = command("activate", "--bundle", str(bundle))
    assert result.returncode == 1
    assert "package changed" in result.stderr
    operations = [json.loads(line) for line in events.read_text().splitlines()]
    assert not any("install" in operation for operation in operations)
    assert operations[-1] == ["--user", "start", "codex-time.service"]
