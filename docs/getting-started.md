# Put your Codex work in focus

Start with one overview of your work, tokens and allowance, then find which projects and sessions account for it. This guide assumes Codex is already installed and you've completed the [terminal setup](../README.md#-ai-coding-in-your-terminal-make-every-session-count). No sudo is needed. Run reports from any directory; open the session picker from the project you want to return to.

## 1. See today's work in one command

```bash
codex-time overview
```

Read total recorded work, tokens and estimated API costs, then allowance and model working time. API estimates are a comparison at Standard API rates, not your subscription bill. Current cycle balance and observed consumption over the selected period answer different questions; missing readings can hide usage, so consumption totals are partial.

Zoom out when you want a broader picture:

```bash
codex-time overview week
codex-time overview month
```

These select the current calendar week or month, not a rolling number of days. Weeks start Monday. Use `--details` for evidence and uncertainty, `--plain` for ASCII output, or `--json` for machine-readable results.

## 2. Find the projects doing the work

```bash
codex-time projects week
```

See directories ranked by recorded work, with their sessions, models, tokens and estimated costs. Omit `week` for today; use `month` or `all` for a longer view. This report includes all directories, wherever you run it.

## 3. Pick up a session where you left off

From your project directory, run:

```bash
codex-time
```

The picker starts with that directory's unarchived sessions. Press `/` to search, `a` to include other directories, and Enter to resume the selected session in its recorded directory. Press `q` to close the picker; background tracking continues.

## 4. Dig deeper only when you need to

| Question | Command |
| --- | --- |
| Which models and reasoning levels did the work this week? | `codex-time model-time week` |
| What evidence supports my allowance consumption rate? | `codex-time allowance week` |
| How much work was recorded each day across projects? | `codex-time history --all-dirs` |
| Is tracking healthy? | `codex-time health` |
| What commands are available? | `codex-time --help` |

Model shares describe recorded work, including tools and delegation; they do not measure each model's quota cost. Parallel root sessions add working time, so totals can exceed elapsed clock time. Unknown or missing evidence stays visible.

## Tracking happens in the background

Setup enables a systemd user service, separate from the picker and reports. You don't need to keep this checkout or a report open. First-time history scanning can take several minutes; an active service alone doesn't prove that scanning has finished. Check `codex-time health` for a fresh heartbeat. Live observation can lag by up to 60 seconds, and tracking stops at logout unless your user manager remains running.

For dates, timezones, storage, privacy and the complete command reference, continue with the [README](../README.md#daily-use-and-cli-commands). For installation or service problems, use the [install guide](../README.md#install).
