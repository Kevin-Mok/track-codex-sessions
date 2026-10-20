# Duplicate mypy input during warmup verification

The warmup emoji verification initially passed both an explicit source file and
the repository directory to mypy. Use one source target to avoid duplicate discovery.

- Symptom/evidence: `.venv/bin/mypy src/codex_time/cli.py .` rejected duplicate
  module `codex_time.cli` before checking types.
- Impact: verification invocation only; the 32 focused regression tests passed.
- Cause: the file was included explicitly and again through `.`.
- Resolution: run `.venv/bin/mypy src/codex_time/cli.py` instead.
- Verification: corrected invocation exited 0: `Success: no issues found in 1 source file`.
- Lookup: searched canonical postmortem memory for `mypy duplicate module`;
  no prior remedy was assumed applicable. The overlapping input paths directly
  explain this invocation error.
- Learning: avoid overlapping mypy targets. Canonical memory registration remains
  outstanding because `~/linux-config/dot_agents/skills/postmortem-memory/`
  is outside this workspace's writable roots; installed copies remain untouched.
