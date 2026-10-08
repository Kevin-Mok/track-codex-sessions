# Overview static verification

Resolve static-check failures before installing the combined report. Runtime tests passed, but strict typing and linting found implementation cleanup still required.

## Symptom, impact and evidence

Initial `.venv/bin/mypy src` exited 1 with 14 errors in overview_output.py: function-scoped row was first inferred as BurnRow and then reused as ModelUsageRow. Initial `.venv/bin/ruff check .` exited 1 with two import-format findings and five long f-string lines. Package build and 35 focused runtime tests passed; installation is deferred until all checks pass.

## Lookup and applicability

Query: `mypy TypedDict loop variable incompatible assignment Ruff line too long`; canonical incident knowledge searched before fixes. The inspected renderer shows reuse of one function-scope loop variable across distinct report contracts. Give reasoning rows a separate name; retain strict public report types. Ruff formatting alone cannot split long string literals; split them explicitly and sort imports.

## Status and next steps

Diagnosed implementation cleanup. Rename reasoning loop variables, split long literals, organize touched imports, and rerun focused tests and static checks. Also verify that narrow plain cohort labels remain ASCII and complete: Rich Rule titles can ellipsize rather than wrap. Keep data/accounting unchanged and record final checks here.

Focused renderer verification now passes 40 tests, including two RED-to-GREEN cases for narrow ASCII cohort labels. Function-scoped TypedDict reuse was removed; short usage names keep multiline literals readable. Initial full suite passed 215 tests before the five additional renderer probes. Final static/broad checks pending.

Guidance follow-up introduced one overlong literal in presentation.py; split it into adjacent strings, keeping output bytes identical. This is the same explicit-string-splitting cleanup already diagnosed. Focused tests passed 68 cases after canonical guidance changes; final typing/lint/build evidence follows.

Resolution: distinct usage loop names satisfy strict TypedDict checking; long literals/imports are formatted explicitly. Wrapping Text labels preserve complete reset evidence and ASCII at 20/32 columns. Fresh full suite passes 224 tests (exit 0); mypy passes 19 sources, Ruff and whitespace pass. Installed source bytes match all seven changed modules; outside-checkout day/week/month JSON matches dedicated reports, all aliases match, fixture storage hashes are unchanged and actual live overview renders grouped work correctly. No data/accounting migration occurred. Existing terminal-report guidance already covers width/plain/runtime checks; the specific Rule-title trap is captured in tasks/lessons.md. No new reusable memory finding is required.
