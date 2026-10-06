"""Convert adjacent fresh samples into bounded work/wait evidence."""

from codex_time.accounting import merge_spans
from codex_time.models import Ledger, Observation, Span, Turn


class Observer:
    def __init__(self, max_gap: float = 3.0) -> None:
        self.previous: dict[str, Observation] = {}
        self.max_gap = max_gap

    def apply(self, ledger: Ledger, samples: list[Observation]) -> None:
        current = {s.session_id: s for s in samples}
        for sid in self.previous:
            if sid not in current:
                self._gap(ledger, sid)
        for sid, sample in current.items():
            session = ledger.sessions.get(sid)
            if session is None:
                continue
            if sample.state == "unknown":
                self._gap(ledger, sid)
                continue
            turns = [
                turn
                for turn in session.turns.values()
                if turn.start <= sample.at
                and (
                    turn.end is None
                    or turn.end >= (self.previous[sid].at if sid in self.previous else sample.at)
                )
            ]
            turn: Turn | None = session.turns.get(sample.turn_id or "")
            if turn is None and turns:
                turn = max(turns, key=lambda t: t.start)
            if turn is None:
                continue
            previous = self.previous.get(sid)
            if previous is None:
                if turn.coverage or turn.waits:
                    self._gap(ledger, sid)
                continue
            elapsed = (sample.at - previous.at).total_seconds()
            if elapsed <= 0:
                continue
            if elapsed > self.max_gap:
                self._gap(ledger, sid)
                continue
            # Do not smear a previous turn's state across a new turn boundary.
            start = max(previous.at, turn.start)
            end = min(sample.at, turn.end) if turn.end is not None else sample.at
            if end <= start:
                continue
            span = Span(start=start, end=end)
            turn.sampling_uncertainty_seconds = max(
                turn.sampling_uncertainty_seconds,
                previous.uncertainty_seconds,
                sample.uncertainty_seconds,
                elapsed,
            )
            if "live_status" not in turn.provenance:
                turn.provenance.append("live_status")
            if previous.state == "working":
                turn.coverage = merge_spans([*turn.coverage, span])
            elif previous.state == "waiting":
                turn.waits = merge_spans([*turn.waits, span])
            if "sampled_waits_1s" not in turn.quality:
                turn.quality.append("sampled_waits_1s")
            if turn.end is None and "unfinished_observed_only" not in turn.quality:
                turn.quality.append("unfinished_observed_only")
        self.previous = current

    @staticmethod
    def _gap(ledger: Ledger, sid: str) -> None:
        session = ledger.sessions.get(sid)
        if session:
            for turn in session.turns.values():
                if turn.end is None and "observation_gap" not in turn.quality:
                    turn.quality.append("observation_gap")
