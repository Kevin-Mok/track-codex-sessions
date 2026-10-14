#!/usr/bin/env python3
"""Prepare, verify, activate or roll back a known Codex Time wheel without sudo.

Preparation reads the installed package and user service and writes a new bundle.
Activation and rollback are explicit operator commands; verification is read-only.
"""

import argparse
import base64
import csv
import fcntl
import hashlib
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import unquote, urlparse

PORTABLE_FILES = (
    "ledger.json",
    "layout.json",
    "quota-observations.jsonl",
    "usage-observations.jsonl",
    "legacy-quota-observations.jsonl",
    "legacy-usage-observations.jsonl",
)
PORTABLE_PATTERNS = (
    "sessions/*.json",
    "projects/*.json",
    "records/*/codex-time-*.json",
    "migration-backup-v1/ledger.json",
    "migration-backup-v1/quota-observations.jsonl",
    "migration-backup-v1/usage-observations.jsonl",
    "migration-backup-v1/manifest.json",
)
RUNTIME_FILES = (
    "checkpoint.json",
    "index.sqlite",
    "index.sqlite-wal",
    "index.sqlite-shm",
    "fx-usd-cad.json",
)


class DeploymentError(RuntimeError):
    pass


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


@contextmanager
def progress(label: str, plain: bool):
    stopped = threading.Event()
    started = time.monotonic()

    def status() -> None:
        while not stopped.wait(10):
            print(
                ("" if plain else "⏳ ") + f"{label}: {time.monotonic() - started:.0f}s elapsed",
                file=sys.stderr,
                flush=True,
            )

    print(("" if plain else "🔎 ") + label, file=sys.stderr, flush=True)
    worker = threading.Thread(target=status, daemon=True)
    worker.start()
    try:
        yield
    finally:
        stopped.set()
        worker.join()


def verify(bundle: Path) -> dict[str, object]:
    expected = (bundle / "manifest.sha256").read_text().strip()
    if digest(bundle / "manifest.json") != expected:
        raise DeploymentError("manifest hash mismatch; preserve and inspect the bundle")
    manifest = json.loads((bundle / "manifest.json").read_bytes())
    if not isinstance(manifest, dict) or manifest.get("version") != 1:
        raise DeploymentError("unsupported deployment manifest version")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise DeploymentError("deployment manifest has no verified artifacts")
    for relative, expected_hash in artifacts.items():
        path = bundle / relative
        if path.is_symlink() or not path.resolve().is_relative_to(bundle.resolve()):
            raise DeploymentError("artifact leaves the verified bundle")
        if digest(path) != expected_hash:
            raise DeploymentError(f"artifact hash mismatch: {relative}")
    return manifest


def run(argv: list[str], *, env: dict[str, str] | None = None) -> str:
    if env is None:
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(argv, capture_output=True, text=True, env=env)
    if completed.returncode:
        diagnostic = (completed.stderr or completed.stdout).strip()[-3000:]
        raise DeploymentError(f"{Path(argv[0]).name} failed: {diagnostic}")
    return completed.stdout


def write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".partial")
    with temporary.open("w") as output:
        json.dump(value, output, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def service(manifest: dict, operation: str) -> str:
    return run([manifest["systemctl"], "--user", operation, manifest["service"]])


def check_unit(bundle: Path, manifest: dict) -> None:
    if service(manifest, "cat") != (bundle / manifest["unit_text"]).read_text():
        raise DeploymentError("user service changed since preparation; prepare a fresh bundle")


def check_installed(manifest: dict, *, expected_key: str = "installed_files") -> None:
    files = manifest.get(expected_key)
    if not isinstance(files, dict) or not files:
        raise DeploymentError("installed package provenance is missing")
    for path, expected in files.items():
        if digest(Path(path)) != expected:
            raise DeploymentError("installed executable/package changed; installation refused")


def validate_operation(bundle: Path, manifest: dict) -> None:
    fields = (
        "systemctl",
        "uv",
        "service",
        "python",
        "recovery_python",
        "recovery_script",
        "new_wheel",
        "previous_wheel",
        "unit_text",
        "data_dir",
        "state_dir",
        "lock",
        "dropin",
    )
    if any(not isinstance(manifest.get(name), str) for name in fields):
        raise DeploymentError("incomplete deployment manifest; no service changes were made")
    argv = manifest.get("unit_argv")
    if not isinstance(argv, list) or not all(isinstance(value, str) for value in argv):
        raise DeploymentError("invalid saved service arguments")
    if not argv or "daemon" not in argv:
        raise DeploymentError("saved service is not a daemon")
    for name in ("recovery_script", "new_wheel", "previous_wheel", "unit_text"):
        if manifest[name] not in manifest["artifacts"]:
            raise DeploymentError("operation references an unverified artifact")
    for name in (
        "systemctl",
        "uv",
        "python",
        "recovery_python",
        "data_dir",
        "state_dir",
        "lock",
        "dropin",
    ):
        if not Path(manifest[name]).is_absolute():
            raise DeploymentError("operation paths must be absolute")
    root, state = Path(manifest["data_dir"]).resolve(), Path(manifest["state_dir"]).resolve()
    if root == state or root.is_relative_to(state) or state.is_relative_to(root):
        raise DeploymentError("tracking data and runtime must be separate")
    for live in (root, state):
        if (
            live == bundle.resolve()
            or live.is_relative_to(bundle.resolve())
            or bundle.resolve().is_relative_to(live)
        ):
            raise DeploymentError("bundle must be separate from tracking data and runtime")
    if Path(manifest["dropin"]).name != "90-codex-time-deployment.conf":
        raise DeploymentError("unexpected rollback drop-in name")


def check_projections(root: Path) -> None:
    """Export copies these trees, so refuse non-tracker files before it starts."""
    for name in ("projects", "records"):
        directory = root / name
        if directory.is_symlink():
            raise DeploymentError("projection directory is a symlink; export refused")
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise DeploymentError("projection contains a symlink; export refused")
            if path.is_dir():
                continue
            value = json.loads(path.read_bytes()) if path.suffix == ".json" else None
            if name == "projects":
                valid = (
                    path.parent == directory
                    and isinstance(value, dict)
                    and set(value) == {"key", "name"}
                    and isinstance(value["name"], str)
                    and isinstance(value["key"], str)
                    and path.name == value["key"] + ".json"
                )
            else:
                valid = (
                    path.parent.parent == directory
                    and path.name.startswith("codex-time-")
                    and isinstance(value, dict)
                    and set(value) == {"start", "end", "project", "is_billable", "tags"}
                    and isinstance(value["start"], str)
                    and isinstance(value["end"], str)
                    and isinstance(value["project"], dict)
                    and set(value["project"]) == {"key"}
                    and value["is_billable"] is False
                    and isinstance(value["tags"], list)
                    and all(
                        isinstance(tag, str) and tag.startswith(("session:", "turn:"))
                        for tag in value["tags"]
                    )
                )
            if not valid:
                raise DeploymentError(
                    "projection contains unrelated/non-tracker files; export refused"
                )


def recovery(bundle: Path, manifest: dict, root: Path, state: Path, *command: str) -> dict:
    raw = run(
        [
            manifest["recovery_python"],
            str(bundle / manifest["recovery_script"]),
            "--data-dir",
            str(root),
            "--state-dir",
            str(state),
            "--plain",
            "--json",
            *command,
        ]
    )
    result = json.loads(raw)
    if not isinstance(result, dict) or result.get("verified") is not True:
        raise DeploymentError("portable history verification did not succeed")
    return result


@contextmanager
def writer_lock(manifest: dict):
    lock = Path(manifest["lock"])
    lock.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with lock.open("a") as file:
        try:
            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise DeploymentError("another tracker writer is active; installation refused") from exc
        yield


def owned_files(root: Path, *, runtime: bool = False):
    for name in RUNTIME_FILES if runtime else PORTABLE_FILES:
        path = root / name
        if path.exists():
            yield path
    for pattern in ("pending-projections/*.json",) if runtime else PORTABLE_PATTERNS:
        yield from root.glob(pattern)


def copy_owned(root: Path, destination: Path, *, runtime: bool = False) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for source in owned_files(root, runtime=runtime):
        if source.is_symlink() or any(p.is_symlink() for p in source.parents if p != root):
            raise DeploymentError("tracker backup refuses symlinks")
        relative = source.relative_to(root)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        expected = digest(source)
        shutil.copyfile(source, target)
        with target.open("rb") as file:
            os.fsync(file.fileno())
        if digest(target) != expected or digest(source) != expected:
            raise DeploymentError("tracker backup hash mismatch; installation refused")
        hashes[str(relative)] = expected
    return hashes


def backup(bundle: Path, manifest: dict) -> dict:
    root, state = Path(manifest["data_dir"]), Path(manifest["state_dir"])
    counts = recovery(bundle, manifest, root, state, "verify")
    check_projections(root)
    target = bundle / ("pre-activation-" + str(time.time_ns()))
    target.mkdir(mode=0o700)
    with writer_lock(manifest):
        hashes = {
            "data": copy_owned(root, target / "data"),
            "runtime": copy_owned(state, target / "runtime", runtime=True),
        }
    copied = recovery(bundle, manifest, target / "data", target / "verify-runtime", "verify")
    for key in ("sessions", "turns", "quota_unique", "usage_unique"):
        if copied.get(key) != counts.get(key):
            raise DeploymentError(f"backup evidence count mismatch: {key}; installation refused")
    result = {"verified": True, "path": str(target), "sha256": hashes, "counts": counts}
    write_json(target / "backup-manifest.json", result)
    return result


def install(bundle: Path, manifest: dict, wheel: str) -> None:
    run(
        [
            manifest["uv"],
            "tool",
            "install",
            "--python",
            manifest["python"],
            "--force",
            "--reinstall-package",
            "codex-time",
            str(bundle / wheel),
        ]
    )


def activate(bundle: Path, manifest: dict) -> dict:
    validate_operation(bundle, manifest)
    check_unit(bundle, manifest)
    check_installed(manifest)
    if (bundle / "activation.json").exists():
        raise DeploymentError("activation already attempted; inspect activation.json or roll back")
    service(manifest, "stop")
    installing = False
    try:
        preserved = backup(bundle, manifest)
        check_installed(manifest)
        check_unit(bundle, manifest)
        result = {"stage": "backup-verified", "backup": preserved}
        write_json(bundle / "activation.json", result)
        installing = True
        result["stage"] = "install-started"
        write_json(bundle / "activation.json", result)
        install(bundle, manifest, manifest["new_wheel"])
        result["stage"] = "installed"
        write_json(bundle / "activation.json", result)
        service(manifest, "start")
        result["stage"] = "active"
        write_json(bundle / "activation.json", result)
        return result
    except (DeploymentError, OSError, ValueError) as exc:
        if not installing:
            service(manifest, "start")
        else:
            raise DeploymentError(
                f"{exc}; service left stopped/failed; verified backup is retained; use rollback"
            ) from exc
        raise


def verify_export(destination: Path, exported: dict) -> None:
    saved = json.loads((destination / "conversion-manifest.json").read_bytes())
    for name, expected in saved["sha256"].items():
        if name not in ("ledger.json", "quota-observations.jsonl", "usage-observations.jsonl"):
            raise DeploymentError("unexpected legacy export artifact")
        if digest(destination / name) != expected:
            raise DeploymentError(f"legacy export hash mismatch: {name}")
    for name in ("sessions", "turns", "quota_unique", "usage_unique"):
        if not (
            saved["source_counts"].get(name)
            == saved["export_counts"].get(name)
            == exported.get(name)
        ):
            raise DeploymentError(f"legacy export evidence mismatch: {name}")


def quoted_unit_argument(value: str) -> str:
    if any(character in value for character in "\n\r\0"):
        raise DeploymentError("service argument contains unsupported control characters")
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return '"' + escaped.replace("%", "%%").replace("$", "$$") + '"'


def rollback(bundle: Path, manifest: dict) -> dict:
    validate_operation(bundle, manifest)
    activation = bundle / "activation.json"
    if not activation.exists():
        raise DeploymentError("this bundle has not activated a package; rollback refused")
    prior = bundle / "rollback.json"
    if prior.exists():
        raise DeploymentError("rollback already attempted; inspect rollback.json before retrying")
    check_unit(bundle, manifest)
    check_installed(manifest, expected_key="new_installed_files")
    dropin = Path(manifest["dropin"])
    if dropin.exists() or dropin.is_symlink():
        raise DeploymentError("rollback drop-in already exists; no service files were replaced")
    service(manifest, "stop")
    installing = False
    try:
        check_projections(Path(manifest["data_dir"]))
        target = bundle / ("rollback-legacy-" + str(time.time_ns()))
        exported = recovery(
            bundle,
            manifest,
            Path(manifest["data_dir"]),
            Path(manifest["state_dir"]),
            "export-legacy",
            str(target),
        )
        verify_export(target, exported)
        runtime = bundle / ("rollback-runtime-" + str(time.time_ns()))
        runtime_hashes: dict[str, str] = {}
        fx = Path(manifest["state_dir"]) / "fx-usd-cad.json"
        if fx.exists():
            if fx.is_symlink():
                raise DeploymentError("FX cache is a symlink; rollback refused")
            validate_fx = (
                "import sys;from pathlib import Path;from codex_time.fx import FXSnapshot;"
                "\ntry:FXSnapshot.model_validate_json(Path(sys.argv[1]).read_bytes())"
                "\nexcept Exception:sys.exit('Invalid FX cache; rollback refused')"
            )
            run([manifest["recovery_python"], "-c", validate_fx, str(fx)])
            expected = digest(fx)
            runtime.mkdir(mode=0o700)
            target_fx = runtime / "fx-usd-cad.json"
            shutil.copyfile(fx, target_fx)
            with target_fx.open("rb") as file:
                os.fsync(file.fileno())
            if digest(fx) != expected or digest(target_fx) != expected:
                raise DeploymentError("FX cache backup hash mismatch; rollback refused")
            runtime_hashes["fx-usd-cad.json"] = expected
        argv = manifest["unit_argv"]
        preserved: list[str] = []
        skip = False
        for argument in argv:
            if skip:
                skip = False
            elif argument in ("--data-dir", "--state-dir"):
                skip = True
            elif not argument.startswith(("--data-dir=", "--state-dir=")):
                preserved.append(argument)
        daemon = preserved.index("daemon")
        restored = (
            preserved[:daemon]
            + [
                "--data-dir",
                str(target),
                "--state-dir",
                str(runtime),
            ]
            + preserved[daemon:]
        )
        unit = (
            "[Service]\nExecStart=\nExecStart="
            + " ".join(quoted_unit_argument(argument) for argument in restored)
            + "\n"
        )
        result = {
            "stage": "export-verified",
            "export": str(target),
            "export_manifest": exported,
            "runtime": str(runtime),
            "runtime_sha256": runtime_hashes,
            "dropin": str(dropin),
            "original_data_preserved": True,
        }
        write_json(prior, result)
        check_installed(manifest, expected_key="new_installed_files")
        check_unit(bundle, manifest)
        installing = True
        result["stage"] = "install-started"
        write_json(prior, result)
        install(bundle, manifest, manifest["previous_wheel"])
        result["stage"] = "previous-package-installed"
        write_json(prior, result)
        dropin.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with dropin.open("x") as output:
            output.write(unit)
            output.flush()
            os.fsync(output.fileno())
        run([manifest["systemctl"], "--user", "daemon-reload"])
        service(manifest, "start")
        result["stage"] = "rolled-back"
        write_json(prior, result)
        return result
    except (DeploymentError, OSError, ValueError, zipfile.BadZipFile) as exc:
        if not installing:
            service(manifest, "start")
        else:
            raise DeploymentError(
                f"{exc}; service left stopped/failed; export is retained; inspect rollback.json"
            ) from exc
        raise


def installed_info(executable: Path) -> dict:
    shebang = executable.read_text().splitlines()[0]
    if not shebang.startswith("#!/") or " " in shebang:
        raise DeploymentError("installed executable must have an absolute Python shebang")
    python = Path(shebang[2:])
    code = (
        "import importlib.metadata as m,json,sys;d=m.distribution('codex-time');"
        "print(json.dumps({'root':str(d.locate_file('')),'version':d.version,"
        "'direct_url':d.read_text('direct_url.json'),'files':[str(p) for p in d.files],"
        "'python':sys.executable}))"
    )
    result = json.loads(run([str(python), "-c", code]))
    result["interpreter"] = str(python.resolve())
    result["executable"] = str(executable)
    return result


def package_files(info: dict):
    root = Path(info["root"])
    for name in info["files"]:
        path = Path(name)
        if path.parts[0] == "codex_time" and "__pycache__" not in path.parts:
            yield name, root / name
        elif len(path.parts) >= 2 and path.parts[0].endswith(".dist-info"):
            if path.name not in ("RECORD", "INSTALLER", "REQUESTED", "direct_url.json"):
                yield name, root / name


def previous_wheel(info: dict, destination: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    records: list[list[str]] = []
    info_dir = ""
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as wheel:
        for name, source in package_files(info):
            body = source.read_bytes()
            value = hashlib.sha256(body).digest()
            wheel.writestr(name, body)
            records.append(
                [
                    name,
                    "sha256=" + base64.urlsafe_b64encode(value).decode().rstrip("="),
                    str(len(body)),
                ]
            )
            hashes[str(source)] = value.hex()
            if name.endswith(".dist-info/WHEEL"):
                info_dir = str(Path(name).parent)
        if not info_dir or not any(row[0] == "codex_time/cli.py" for row in records):
            raise DeploymentError(
                "installed package is editable/incomplete; wheel recovery refused"
            )
        records.append([info_dir + "/RECORD", "", ""])
        output = io.StringIO()
        csv.writer(output, lineterminator="\n").writerows(records)
        wheel.writestr(info_dir + "/RECORD", output.getvalue())
    hashes[info["executable"]] = digest(Path(info["executable"]))
    return hashes


def unit_arguments(text: str, executable: Path) -> list[str]:
    argv: list[str] = []
    for line in text.splitlines():
        if line.startswith(("Environment=", "EnvironmentFile=", "ExecStartPre=", "ExecStartPost=")):
            raise DeploymentError("complex unit environment/hooks require manual deployment review")
        if line.startswith("ExecStart="):
            value = line.removeprefix("ExecStart=")
            if not value:
                argv = []
            elif argv:
                raise DeploymentError("multiple service commands require manual deployment review")
            else:
                if any(character in value for character in ("$", "%", "\\")):
                    raise DeploymentError("expanded/escaped unit arguments require manual review")
                argv = shlex.split(value)
    if not argv or Path(argv[0]).resolve() != executable.resolve() or "daemon" not in argv:
        raise DeploymentError("unit must run the captured codex-time executable with daemon")
    return argv


def option(argv: list[str], name: str, default: Path) -> Path:
    for index, value in enumerate(argv):
        if value == name:
            path = Path(argv[index + 1])
            break
        if value.startswith(name + "="):
            path = Path(value.split("=", 1)[1])
            break
    else:
        path = default
    if not path.is_absolute():
        raise DeploymentError(f"relative {name} requires manual deployment review")
    return path.resolve()


def prepare(args: argparse.Namespace) -> dict:
    wheel = args.wheel.expanduser().resolve()
    if not wheel.is_file() or wheel.suffix != ".whl":
        raise DeploymentError("new wheel does not exist or is not a wheel file")
    with zipfile.ZipFile(wheel) as archive:
        if "codex_time/recovery.py" not in archive.namelist():
            raise DeploymentError("new wheel lacks the lossless recovery module")
    bundle = args.destination.expanduser().resolve()
    if bundle.exists():
        raise DeploymentError("preparation requires a fresh destination; existing files preserved")
    uv = str(Path(shutil.which(args.uv) or args.uv).resolve())
    systemctl = str(Path(shutil.which(args.systemctl) or args.systemctl).resolve())
    tool_dir = Path(run([uv, "tool", "dir"]).strip()).resolve()
    bin_dir = Path(run([uv, "tool", "dir", "--bin"]).strip())
    executable = args.installed_executable or bin_dir / "codex-time"
    executable = executable.expanduser().absolute()
    if executable.resolve().parent.parent != tool_dir / "codex-time":
        raise DeploymentError("installed executable is not the current uv codex-time tool")
    info = installed_info(executable)
    unit_text = run([systemctl, "--user", "cat", args.service])
    argv = unit_arguments(unit_text, executable)
    root = option(argv, "--data-dir", Path.home() / ".codex-timetrace")
    base_state = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
    identity = hashlib.sha256(str(root).encode()).hexdigest()[:24]
    state = option(argv, "--state-dir", base_state / "codex-time" / identity)
    for live in (root, state):
        if bundle == live or bundle.is_relative_to(live) or live.is_relative_to(bundle):
            raise DeploymentError("bundle must be separate from tracking data and runtime")
    bundle.mkdir(parents=True, mode=0o700)
    new = bundle / "new" / wheel.name
    new.parent.mkdir()
    shutil.copyfile(wheel, new)
    previous = bundle / "previous" / f"codex_time-{info['version']}-py3-none-any.whl"
    previous.parent.mkdir()
    installed_hashes = previous_wheel(info, previous)
    with zipfile.ZipFile(new) as archive:
        new_installed_files = {
            str(Path(info["root"]) / name): hashlib.sha256(archive.read(name)).hexdigest()
            for name in archive.namelist()
            if name.startswith("codex_time/") and not name.endswith("/")
        }
    (bundle / "unit.txt").write_text(unit_text)
    shutil.copyfile(Path(__file__), bundle / "deployment.py")
    shutil.copyfile(Path(__file__).with_name("storage-recovery.py"), bundle / "recover.py")
    environment = dict(os.environ)
    environment["UV_CACHE_DIR"] = str(bundle / ".uv-cache")
    environment["UV_PYTHON_INSTALL_DIR"] = str(bundle / ".uv-python")
    environment["UV_PYTHON_DOWNLOADS"] = "never"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment.pop("PYTHONPATH", None)
    run(
        [uv, "venv", "--python", info["interpreter"], str(bundle / "recovery-env")], env=environment
    )
    recovery_python = bundle / "recovery-env/bin/python"
    run([uv, "pip", "install", "--python", str(recovery_python), str(new)], env=environment)
    artifacts = {
        str(path.relative_to(bundle)): digest(path)
        for path in (
            new,
            previous,
            bundle / "unit.txt",
            bundle / "deployment.py",
            bundle / "recover.py",
        )
    }
    for path in (bundle / "recovery-env").rglob("*"):
        if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts:
            artifacts[str(path.relative_to(bundle))] = digest(path)
    direct = json.loads(info["direct_url"] or "null")
    provenance: dict = {"installed_direct_url": direct, "installed_version": info["version"]}
    if isinstance(direct, dict) and isinstance(direct.get("url"), str):
        parsed = urlparse(direct["url"])
        checkout = Path(unquote(parsed.path)) if parsed.scheme == "file" else None
        if checkout and (checkout / ".git").exists():
            provenance["checkout"] = str(checkout)
            provenance["checkout_head"] = run(
                ["git", "-C", str(checkout), "rev-parse", "HEAD"]
            ).strip()
            provenance["checkout_status"] = run(["git", "-C", str(checkout), "status", "--short"])
    config = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    manifest = {
        "version": 1,
        "artifacts": artifacts,
        "new_wheel": str(new.relative_to(bundle)),
        "previous_wheel": str(previous.relative_to(bundle)),
        "unit_text": "unit.txt",
        "unit_argv": argv,
        "systemctl": systemctl,
        "uv": uv,
        "service": args.service,
        "python": info["interpreter"],
        "installed_files": installed_hashes,
        "new_installed_files": new_installed_files,
        "recovery_python": str(recovery_python),
        "recovery_script": "recover.py",
        "data_dir": str(root),
        "state_dir": str(state),
        "provenance": provenance,
        "lock": str(Path.home() / ".local/state/codex-time/locks" / identity / "writer.lock"),
        "dropin": str(
            config / "systemd/user" / (args.service + ".d") / "90-codex-time-deployment.conf"
        ),
        "limitations": [
            "Previous wheel preserves installed files, not an older PID's bytecode.",
            "Rollback keeps original data and selects a verified export with a fresh runtime.",
            "Failed/interrupted installation leaves the service stopped; inspect stage manifests.",
        ],
    }
    write_json(bundle / "manifest.json", manifest)
    (bundle / "manifest.sha256").write_text(digest(bundle / "manifest.json") + "\n")
    verify(bundle)
    return {
        "prepared": True,
        "verified": True,
        "bundle": str(bundle),
        "live_service_unchanged": True,
        "provenance": provenance,
        "limitations": manifest["limitations"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--json", action="store_true")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("prepare", help="read live provenance and prepare a fresh bundle")
    create.add_argument("--wheel", type=Path, required=True)
    create.add_argument("--destination", type=Path, required=True)
    create.add_argument("--installed-executable", type=Path)
    create.add_argument("--uv", default="uv")
    create.add_argument("--systemctl", default="systemctl")
    create.add_argument("--service", default="codex-time.service")
    for name in ("verify", "activate", "rollback"):
        check = commands.add_parser(name)
        check.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    try:
        with progress("Checking deployment bundle and " + args.command, args.plain):
            if args.command == "prepare":
                result = prepare(args)
                manifest = None
            else:
                manifest = verify(args.bundle)
            if args.command == "activate":
                result = activate(args.bundle, manifest)
            elif args.command == "rollback":
                result = rollback(args.bundle, manifest)
            elif args.command == "verify":
                result = {"verified": True, "bundle": str(args.bundle.resolve())}
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(("" if args.plain else "✅ ") + f"Deployment {args.command} complete")
            print(json.dumps(result, indent=2))
        return 0
    except (DeploymentError, OSError, ValueError) as exc:
        print(("" if args.plain else "⚠️ ") + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
