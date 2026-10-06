"""Repeated setup deploys changed local source using disposable tools/service state."""

import os
import shutil
import subprocess
from pathlib import Path


def test_setup_rebuilds_changed_source_with_unchanged_version(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    package = tmp_path / "project"
    (package / "scripts").mkdir(parents=True)
    (package / "systemd").mkdir()
    (package / "src/codex_time").mkdir(parents=True)
    shutil.copy(repo / "scripts/setup.sh", package / "scripts/setup.sh")
    shutil.copy(repo / "systemd/codex-time.service", package / "systemd/codex-time.service")
    (package / "pyproject.toml").write_text(
        '[build-system]\nrequires=["hatchling"]\nbuild-backend="hatchling.build"\n'
        '[project]\nname="codex-time"\nversion="0.0.1"\nrequires-python=">=3.12"\n'
        '[project.scripts]\ncodex-time="codex_time:main"\n'
    )
    source = package / "src/codex_time/__init__.py"
    source.write_text('def main():\n    print("old source")\n')
    binaries = tmp_path / "bin"
    binaries.mkdir()
    (binaries / "systemctl").write_text("#!/bin/sh\nexit 0\n")
    (binaries / "systemctl").chmod(0o755)
    uv = shutil.which("uv")
    assert uv
    # Exercise real local builds without network or the user's installed tools.
    (binaries / "uv").write_text(f'#!/bin/sh\nexec "{uv}" --offline "$@"\n')
    (binaries / "uv").chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{binaries}:{os.environ['PATH']}",
        "UV_TOOL_DIR": str(tmp_path / "tools"),
        "UV_TOOL_BIN_DIR": str(tmp_path / "tool-bin"),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
    }

    def setup() -> None:
        result = subprocess.run(
            ["bash", str(package / "scripts/setup.sh")], env=env, text=True, capture_output=True
        )
        assert result.returncode == 0, result.stderr

    setup()
    executable = tmp_path / "tool-bin/codex-time"
    assert subprocess.check_output([str(executable)], text=True).strip() == "old source"
    source.write_text('def main():\n    print("new source")\n')
    setup()
    assert subprocess.check_output([str(executable)], text=True).strip() == "new source"
