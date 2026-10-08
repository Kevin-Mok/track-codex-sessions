# Session plan staging whitespace

The staged-diff check found one trailing blank line while isolating this session's plan from another session's appended notes. Normalize only the staged plan ending, then rerun the staged whitespace and feature checks.

## Symptom, impact and evidence

`git diff --cached --check` reported `plans/daily-repo-session-time.md:74: new blank line at EOF.` The surrounding command continued to its next read-only inspection and returned 0, so that wrapper status did not establish a passing whitespace check. No commit or push had occurred; other-session working-tree changes remained intact.

## Lookup, cause and next steps

Canonical-memory lookup `git diff check new blank line EOF` returned no matching finding and was run before remediation. The direct diagnostic identifies a local serialization boundary: splitting the shared plan before its rerun heading retained its Markdown section separator at the staged EOF. Strip trailing blank lines in the index-only version, preserving the worktree and other-session notes. Verify the exact staged snapshot and update reviewed incident coverage. Resolution: the index-only plan now ends with one newline. Fresh `git diff --cached --check` exited 0. The working-tree plan and all excluded rerun hunks stayed intact. The original feature's staged source is unchanged; validation runs against a checkout of the exact index. A local engineering lesson records this staging boundary; no new general canonical-memory finding is needed.
