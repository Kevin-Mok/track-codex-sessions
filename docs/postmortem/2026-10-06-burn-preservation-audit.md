# Allowance upgrade timing preservation audit

This report records a strict-equality audit failure during allowance tracking installation. Check whether historical evidence was added or lost before accepting preservation; avoid changing valid timing reconciliation to satisfy a snapshot assertion.

## Symptom and impact

On 2026-10-06, a preservation audit expected zero changed completed turns but found one wait-list difference. The audit checked **42,472 completed turns**: **0 missing turns, 0 start changes, 0 end changes, 0 coverage changes, 0 model-context changes, and 1 wait-list change**. No lost IDs were observed. The timestamp comparison subsequently established additive historical evidence with no counted-time change.

## Lookup and diagnostic evidence

Read the canonical postmortem-memory skill, searched `model report preservation audit additive historical wait reimport`, and inspected `docs/postmortem/2026-10-06-model-report-preservation-audit.md`. The earlier verified audit found lawful additive historical wait reconciliation and a precise end replacement; it specifically warned that raw equality is stricter than evidence preservation. That prior report applies as an investigation pattern, not proof that the current difference is lawful.

The content-free comparison identified an added historical wait `16:30:20.230` → `16:30:53.313`, entirely contained in an existing wait ending `16:30:54.036033`. All old waits remain present; merged wait unions are identical. No product code correction was needed.

## Current status and next steps

Status: **verified_fix** for the audit assertion; root-cause confidence: **confirmed**; verification scope: **code**.

The corrected evidence-preservation audit exited **0**: all **42,472 completed turns** retain exact start/end, coverage and model-context evidence; every old wait is preserved; merged wait unions are identical. This preserves the substantive timing requirement while allowing redundant recorded evidence. Raw list equality was the incorrect audit invariant, not a product defect. Historical reimport remains additive and counted timing is unchanged.

## Learning review

Final review: explicit no-new-learning. This repeats the prior verified additive-evidence audit principle: preserve old spans and compare merged unions rather than raw list equality when reimport adds redundant historical evidence. Canonical registration records the final report hash and alias; no app source was changed for this audit incident.
