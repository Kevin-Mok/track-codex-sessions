# Tracker latency task terminal navigation

Record a terminal-navigation failure while handing the verified tracker-latency prompt to a fresh executor. Preserve the already-started task, distinguish navigation from execution, and verify access before retrying navigation.

## Symptom, impact, and evidence

On 2026-10-22 the native create-thread call returned executor `01a1649b-7157-7b11-bea1-637ac46c0b36`. Native read-thread confirmed it was active and had read `prompts/optimize-cli-latency.md`. Native list-threads confirmed the compiler title `Launch tracker latency task` for `01a16494-02f4-7261-931c-a3e4e11fa3f2`.

The first sandboxed invocation of `/home/kevin/.agents/skills/metaprompt-run/scripts/open_thread.py` with that executor ID, source title, repository cwd and `--details` exited 1: `Found 0 source windows for 'Launch tracker latency task'; need exactly one.` It did not verify a terminal tab. The executor remains started; no duplicate create-thread call or prompt resend is needed. No product/runtime data was changed by this failure.

## Current status and next steps

Navigation resolved through the normal scoped approval route, using the same executor ID and source title. The approved helper exited 0 and reported: `Opened and verified thread 01a1649b-7157-7b11-bea1-637ac46c0b36 in Kitty window 2 via unix:/tmp/kitty-397559`. No second executor was created. A subsequent native read-thread returned active/inProgress with diagnostic commands and progress messages, confirming that execution continues separately from navigation.

## Root cause, resolution, and verification

The same helper, ID, title, and cwd succeeded when given approved host socket access. This establishes a verified navigation workaround and supports restricted socket visibility as the cause of the failed default-context discovery; it does not prove the underlying namespace mechanism or repair the sandbox. No helper, terminal configuration, product code, or service change was necessary. Executor application-performance completion remains separate and unclaimed.

## Lookup and learning

Queries `Kitty source window socket sandbox navigation`, `metaprompt-run`, and `source windows` returned no directly applicable verified navigation finding. Returned titlebar, key-encoding, and preview-PATH guidance concerns different symptoms and was not used as a remedy. The current metaprompt-run skill itself explicitly warns that socket control may require scoped approval and that a failed sandbox probe does not establish Kitty absence; that instruction and the actual helper results justified the scoped retry.

Review decision: no new durable learning is needed because the authorized socket fallback and reuse of the existing executor ID are already explicit in the active skill. Register this report's final scan hash/alias in the canonical ledger with that specific decision; record the targeted coverage-check result in `plans/optimize-cli-latency.md` to avoid changing the reviewed report after registration. Keep pre-existing handoff reports untouched. Remaining limitation: ordinary sandbox socket visibility was not repaired; application speedup is still being measured by the executor.
