# Timetrace source discovery returned 404

A read-only compatibility investigation guessed two source-file paths that do not exist. Use the repository tree to locate native JSON types before implementing compatibility checks.

## Symptom and impact

On 2026-10-06, curl to timetrace v0.14.3 root record.go and project.go returned HTTP 404. No application, Codex, or timetrace data changed. The config/config.go fetch succeeded. Test-module absence is deliberate pre-implementation RED and is excluded from this incident.

## Evidence and current status

The raw HTTP responses reported `curl: (22) ... 404`; the combined shell command exited 0 because its final fetch succeeded. Resolved by repository tree discovery; native types are in core/record.go and core/project.go, not root-level files. Prevention: inspect the tree before fetching specific source files and inspect every nested result rather than only aggregate exit status.

## Lookup and applicability

Query: `GitHub raw source 404 guessed path`. The lookup returned local-current-source-retrieval and local-discover-paths-before-reads; their versioned-tree discovery guidance applies to the wrong filename. Diagnostic evidence is the two URL paths and HTTP 404.

## Resolution and verification

Use GitHub's versioned tree and retrieve the listed type source. Verification evidence will be recorded after discovery and isolated native reader checks. Root cause confidence: high (missing files at guessed paths). No repair to existing data required.

## Follow-up and rollback

Keep native compatibility fixtures isolated. No rollback needed for these read-only HTTP requests. This incident is a source-discovery mistake; no new reusable engineering learning beyond existing source-verification guidance.

## Additional integration diagnostics

The live-adapter verification exposed Ruff B007 for a test-loop variable referenced through a server closure, and an initial direct Python probe could not import the not-yet-reinstalled source package. The adapter changed to an explicit next_phase assignment and repeated the probe with PYTHONPATH=src. Its 10 tests, focused mypy, and actual read-only socket poll passed (17 loaded sessions: 13 idle, 4 working). These were development checks, not production incidents; fixture/packaging diagnostics are tracked here before retries. A full installation will verify the packaged entry point without PYTHONPATH.

Adapter integration also found three mypy annotation issues (optional Session reuse and an untyped index ID) and first-run lint formatting/UTC alias findings. Focused fixes passed mypy and Ruff. The initial presentation lint reported line lengths and imports; its formatted implementation then passed. A direct metadata Python probe reproduced the source-package import problem; tests inject src, so packaged installation must be checked independently. This is fixture/packaging verification work, with no change to Codex or existing records.

The first whole-project mypy check found a reused `previous` loop variable inferred as Observation before assignment of an optional lookup; rename the unused first loop variable. The first whole-project Ruff check found 15 import, UTC-alias, loop-name and formatting findings. These are mechanical integration fixes; focused behavior tests remain green. Wheel/sdist build and reinstalled editable package import already pass. Prior memory lookup returned type/import integration findings, applicable only to checking source imports and annotations, not timing behavior.


## Completed verification

Versioned GitHub tree discovery identified core/record.go and core/project.go; both exact source reads succeeded. Reinstalled editable package imports from src correctly, wheel/source builds pass, and the uv-installed command plus real user service are active. Formatting and strict annotations pass. Native fixture verification confirms two distinct within-minute files and 30 seconds in exported reports. Status: resolved; no new reusable learning beyond existing source-discovery and integration-boundary guidance. This report consolidates mechanical first-pass development checks; intentional RED tests are excluded.
