"""Short human caveats; complete recording evidence stays in JSON exports."""

from collections.abc import Sequence


def quality_note(quality: Sequence[str]) -> str:
    if not quality:
        return ""
    notes = []
    if any(flag.startswith("sampled_waits") for flag in quality):
        notes.append("waits are sampled")
    if "historical_upper_bound" in quality:
        notes.append("some work is estimated")
    if "observation_gap" in quality:
        notes.append("recording gaps")
    if "unfinished_observed_only" in quality or "unfinished" in quality:
        notes.append("unfinished work")
    if not notes:
        notes.append("some recording evidence is uncertain")
    return "; ".join(notes).capitalize() + "."


def diagnostic_note(diagnostics: Sequence[str]) -> str:
    count = len(set(diagnostics))
    if not count:
        return ""
    noun = "notice" if count == 1 else "notices"
    return f"{count} recording {noun}; full evidence: --json."
