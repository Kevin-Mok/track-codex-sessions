"""Validated, content-free interfaces shared by adapters and storage."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RuntimeState = Literal["working", "waiting", "idle", "unknown"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Span(Model):
    start: datetime
    end: datetime

    @field_validator("start", "end")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp requires an explicit timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def ordered(self) -> "Span":
        if self.end < self.start:
            raise ValueError("end precedes start")
        return self


class ModelContext(Model):
    at: datetime
    model_id: str | None = None
    reasoning_level: str | None = None
    provenance: Literal["rollout.turn_context"] = "rollout.turn_context"

    @field_validator("at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("model context requires timezone")
        return value.astimezone(UTC)


class Turn(Model):
    id: str
    cwd: str
    start: datetime
    end: datetime | None = None
    model_contexts: list[ModelContext] = Field(default_factory=list)
    waits: list[Span] = Field(default_factory=list)
    coverage: list[Span] = Field(default_factory=list)
    quality: list[str] = Field(default_factory=lambda: ["historical_upper_bound"])
    outcome: str | None = None
    provenance: list[str] = Field(default_factory=lambda: ["rollout"])
    sampling_uncertainty_seconds: float = Field(default=0, ge=0, allow_inf_nan=False)

    @field_validator("start", "end")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                raise ValueError("timestamp requires timezone")
            return value.astimezone(UTC)
        return value

    @model_validator(mode="after")
    def ordered(self) -> "Turn":
        if self.end is not None and self.end < self.start:
            raise ValueError("turn end precedes start")
        return self


class Session(Model):
    id: str
    cwd: str
    title: str = ""
    created: datetime
    updated: datetime
    archived: bool = False
    parent_id: str | None = None
    is_child: bool = False
    turns: dict[str, Turn] = Field(default_factory=dict)
    quality: list[str] = Field(default_factory=list)

    @field_validator("created", "updated")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp requires timezone")
        return value.astimezone(UTC)


class QuotaObservation(Model):
    at: datetime
    limit_id: str = Field(min_length=1, max_length=128)
    plan_type: str | None = Field(default=None, max_length=128)
    bucket: Literal["primary", "secondary"]
    window_minutes: int = Field(gt=0, strict=True)
    resets_at: int = Field(ge=0, strict=True)
    used_percent: float = Field(ge=0, le=100, allow_inf_nan=False, strict=True)
    provenance: Literal["rollout.token_count.rate_limits"] = "rollout.token_count.rate_limits"

    @field_validator("at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("quota observation requires timezone")
        return value.astimezone(UTC)


class TokenCounts(Model):
    """Exact token categories; absence is different from a measured zero."""

    input_tokens: int | None = Field(default=None, ge=0, strict=True)
    cached_input_tokens: int | None = Field(default=None, ge=0, strict=True)
    cache_write_input_tokens: int | None = Field(default=None, ge=0, strict=True)
    output_tokens: int | None = Field(default=None, ge=0, strict=True)
    reasoning_output_tokens: int | None = Field(default=None, ge=0, strict=True)
    total_tokens: int | None = Field(default=None, ge=0, strict=True)


class UsageObservation(Model):
    """Whitelisted rollout evidence and its conservative, replayable increment."""

    id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    at: datetime
    cwd: str | None = None
    model_id: str | None = None
    turn_id: str | None = None
    cumulative: TokenCounts | None = None
    last_usage: TokenCounts | None = None
    delta: TokenCounts | None = None
    request_input_tokens: int | None = Field(default=None, ge=0, strict=True)
    diagnostics: list[str] = Field(default_factory=list)

    @field_validator("at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("usage observation requires timezone")
        return value.astimezone(UTC)


class Ledger(Model):
    version: Literal[4] = 4

    @model_validator(mode="before")
    @classmethod
    def upgrade(cls, value: object) -> object:
        if isinstance(value, dict) and value.get("version") in (1, 2, 3):
            return {**value, "version": 4}
        return value

    sessions: dict[str, Session] = Field(default_factory=dict)
    quota_observations: list[QuotaObservation] = Field(default_factory=list)
    usage_observations: list[UsageObservation] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class Observation(Model):
    session_id: str
    state: RuntimeState
    at: datetime
    turn_id: str | None = None
    cwd: str | None = None
    uncertainty_seconds: float = Field(default=1, ge=0, allow_inf_nan=False)
    # Runtime state only; never carry messages/items from thread/read.

    @field_validator("at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp requires timezone")
        return value.astimezone(UTC)


class WorkSegment(Span):
    cwd: str
    turn_ids: list[str]
    quality: list[str]


class AttributedSegment(WorkSegment):
    model_id: str | None = None
    reasoning_level: str | None = None
