"""Bound memory/time while skipping escaped message bodies."""

import os
import subprocess
import sys


def run_selector(body: str, timeout: float = 8) -> subprocess.CompletedProcess[str]:
    # A separate limited process makes the RED safe on a real workstation.
    program = '''
import resource
resource.setrlimit(resource.RLIMIT_AS, (192 * 1024 * 1024, 192 * 1024 * 1024))
from codex_time.ingest import content_free_record
''' + body
    return subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=dict(os.environ),
    )


def test_dense_escaped_ignored_string_has_bounded_memory() -> None:
    result = run_selector(r'''
prefix = b'{"type":"response_item","payload":{"type":"message","content":"'
raw = prefix + b'\\n' * 2_000_000 + b'"}}'
assert content_free_record(raw) == {"type": "response_item", "payload": {"type": "message"}}
print("selected content-free fields within memory limit")
''')
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "selected content-free fields within memory limit"


def test_invalid_ignored_string_does_not_backtrack_exponentially() -> None:
    result = run_selector(r'''
raw = b'{"type":"response_item","payload":{"type":"message","content":"' + b'a' * 1_000 + b'\\q"}}'
try:
    content_free_record(raw)
except ValueError:
    print("invalid source rejected")
else:
    raise AssertionError("invalid escape accepted")
''', timeout=4)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "invalid source rejected"
