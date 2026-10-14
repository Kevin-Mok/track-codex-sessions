"""Conservative cumulative token arithmetic, independent of report-time pricing."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from pydantic import Field

from codex_time.models import Model, TokenCounts, UsageObservation

TOKEN_FIELDS = tuple(TokenCounts.model_fields)


class UsageState(Model):
    """Content-free checkpoint state needed to continue a cumulative sequence."""

    cumulative: TokenCounts | None = None
    model_id: str | None = None
    turn_id: str | None = None
    context_at: datetime | None = None
    created: datetime | None = None
    forked: bool = False
    child: bool = False
    cwd_known: bool = True
    gap: bool = False
    model_changed: bool = False
    cwd_changed: bool = False
    models_seen: list[str | None] = Field(default_factory=list)
    directories_seen: list[str] = Field(default_factory=list)


def token_counts(raw: object, diagnostics: list[str]) -> TokenCounts | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        diagnostics.append("invalid_token_counts")
        return None
    values: dict[str, int | None] = {}
    for name in TOKEN_FIELDS:
        value = raw.get(name)
        if value is not None and (type(value) is not int or value < 0):
            diagnostics.append(f"invalid_{name}")
            value = None
        values[name] = value
    return TokenCounts.model_validate(values)


def increment(
    current: TokenCounts | None,
    previous: TokenCounts | None,
    state: UsageState,
    diagnostics: list[str],
) -> TokenCounts | None:
    if current is None:
        diagnostics.append("missing_cumulative_usage")
        return None
    if previous is None:
        if state.forked or state.gap:
            diagnostics.append(
                "fork_baseline_unavailable" if state.forked else "baseline_unavailable"
            )
            return None
        return current.model_copy()
    values: dict[str, int | None] = {}
    for name in TOKEN_FIELDS:
        now, old = getattr(current, name), getattr(previous, name)
        if now is not None and old is not None and now < old:
            diagnostics.append("counter_reset")
            return None
        values[name] = now - old if now is not None and old is not None else None
    result = TokenCounts.model_validate(values)
    if all(value in (None, 0) for value in values.values()):
        diagnostics.append("repeated_cumulative_usage")
    if any(
        getattr(current, name) is not None and getattr(previous, name) is None
        for name in TOKEN_FIELDS
    ):
        diagnostics.append("category_baseline_unavailable")
    return result


def request_input(delta: TokenCounts | None, last: TokenCounts | None) -> int | None:
    """Only an entire proven request may select a request-level context price tier."""
    if delta is None or last is None:
        return None
    if any(
        getattr(delta, name) is None or getattr(delta, name) != getattr(last, name)
        for name in ("input_tokens", "output_tokens", "total_tokens")
    ):
        return None
    if not delta.total_tokens:
        return None
    if any(getattr(delta, name) != getattr(last, name) for name in TOKEN_FIELDS):
        return None
    return delta.input_tokens


def observe(
    raw: object,
    *,
    session_id: str,
    cwd: str,
    at: datetime,
    state: UsageState,
) -> UsageObservation | None:
    """Process one observation in source order; inherited fork snapshots only seed state."""
    diagnostics: list[str] = []
    info = raw if isinstance(raw, dict) else {}
    current = token_counts(info.get("total_token_usage"), diagnostics)
    last = token_counts(info.get("last_token_usage"), diagnostics)
    if state.child and state.cumulative is None and request_input(current, last) is None:
        delta = None
        diagnostics.append("child_baseline_unavailable")
    else:
        delta = increment(current, state.cumulative, state, diagnostics)
    if current is not None:
        state.cumulative = current
    if state.created is not None and at < state.created:
        # Forked rollouts can contain verbatim historical events. They establish
        # a baseline but were already consumed by the source session.
        return None
    matched_input = request_input(delta, last)
    model_id = state.model_id
    directory = (cwd or None) if state.cwd_known else None
    if state.gap:
        model_id = state.model_id = None
        directory = None
        state.cwd_known = False
        diagnostics.append("source_gap_attribution_unavailable")
    if state.context_at is not None and state.context_at > at:
        model_id = None
        directory = None
        diagnostics.append("context_timestamp_after_usage")
    if state.model_changed and matched_input is None:
        model_id = None
        diagnostics.append("ambiguous_model_attribution")
    if state.cwd_changed and matched_input is None:
        directory = None
        diagnostics.append("ambiguous_directory_attribution")
    if model_id is None:
        diagnostics.append("unknown_model")
    if directory is None:
        diagnostics.append("unknown_directory")
    if (
        delta is not None
        and matched_input is None
        and "repeated_cumulative_usage" not in diagnostics
    ):
        diagnostics.append("request_billing_evidence_unavailable")
    identity = json.dumps(
        [
            session_id,
            at.isoformat(),
            current.model_dump() if current is not None else None,
            last.model_dump() if last is not None else None,
        ],
        sort_keys=True,
    )
    observation = UsageObservation(
        id=hashlib.sha256(identity.encode()).hexdigest(),
        session_id=session_id,
        at=at,
        cwd=directory,
        model_id=model_id,
        turn_id=state.turn_id,
        cumulative=current,
        last_usage=last,
        delta=delta,
        request_input_tokens=matched_input,
        diagnostics=diagnostics,
    )
    if current is not None:
        state.model_changed = False
        state.cwd_changed = False
        state.models_seen = [state.model_id]
        state.directories_seen = [cwd]
        state.gap = False
    return observation
