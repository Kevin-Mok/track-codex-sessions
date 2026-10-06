"""Allowance evidence and replay specification; only sanitized fixtures."""

import csv
import io
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from codex_time.cli import parser
from codex_time.ingest import RolloutReader
from codex_time.models import Ledger, ModelContext, Session, Span, Turn
from codex_time.storage import Store

BASE = datetime(2026, 10, 6, 16, tzinfo=UTC)


def reading(seconds: int, used: float, reset: int = 1791760139, **extra: object) -> dict:
    return dict(
        at=BASE + timedelta(seconds=seconds),
        used_percent=used,
        resets_at=reset,
        window_minutes=10080,
        bucket="primary",
        limit_id="codex",
        plan_type="pro",
        **extra,
    )


def ledger_with_work(roots: int = 1, child: bool = False) -> Ledger:
    sessions = {}
    for i in range(roots + int(child)):
        turn = Turn(
            id="turn",
            cwd="/work",
            start=BASE,
            end=BASE + timedelta(seconds=600),
            model_contexts=[ModelContext(at=BASE, model_id="A", reasoning_level="high")],
        )
        sessions[str(i)] = Session(
            id=str(i),
            cwd="/work",
            created=BASE,
            updated=turn.end,
            turns={"turn": turn},
            is_child=i >= roots,
        )
    return Ledger(sessions=sessions)


def run_report(ledger: Ledger, readings: list[dict], **kwargs: object) -> dict:
    from codex_time.burn import burn_report
    from codex_time.models import QuotaObservation

    ledger.quota_observations = [QuotaObservation(**r) for r in readings]
    return burn_report(ledger, period="day", selected_date=date(2026, 10, 6), **kwargs)


def test_cli_supports_reproducible_allowance_reports() -> None:
    args = parser().parse_args(["burn", "week", "--date", "2026-10-06", "--json"])
    assert args.command == "burn" and args.window_minutes == 10080
    assert args.max_gap_seconds == 600 and args.limit_id == "codex"
    with pytest.raises(SystemExit):
        parser().parse_args(["burn", "day", "--json", "--csv"])


def test_waits_concurrent_roots_children_and_mix() -> None:
    ledger = ledger_with_work(2, child=True)
    ledger.sessions["0"].turns["turn"].waits = [Span(start=BASE, end=BASE + timedelta(seconds=120))]
    ledger.sessions["1"].turns["turn"].model_contexts.append(
        ModelContext(at=BASE + timedelta(seconds=300), model_id="B", reasoning_level="max")
    )
    data = run_report(ledger, [reading(0, 10), reading(600, 13)])
    row = data["rows"][0]
    assert row["matched_points"] == 3
    assert row["working_microseconds"] == 1080_000_000
    assert row["points_per_working_hour"] == 10
    assert sum(m["working_microseconds"] for m in row["mix"]) == 1080_000_000
    assert {m["model_id"] for m in row["mix"]} == {"A", "B"}
    assert "historical_upper_bound" in row["quality"]


def test_gaps_no_work_and_zero_drop_are_explicit() -> None:
    data = run_report(
        ledger_with_work(), [reading(0, 10), reading(300, 10), reading(1200, 15), reading(1300, 16)]
    )
    row = data["rows"][0]
    assert row["matched_points"] == 0 and row["working_microseconds"] == 300_000_000
    assert row["points_per_working_hour"] == 0
    assert row["excluded_gap_points"] == 5 and row["excluded_no_work_points"] == 1
    assert run_report(Ledger(), [])["rows"] == []


def test_manual_reset_jitter_stale_readings_and_duplicate_snapshots() -> None:
    data = run_report(
        ledger_with_work(),
        [
            reading(0, 10),
            reading(100, 11, reset=1791760141),
            reading(150, 10),
            reading(200, 12),
            reading(200, 12),
            reading(300, 1, reset=1791846539),
            reading(400, 3, reset=1791846539),
        ],
    )
    assert len(data["rows"]) == 2
    assert [r["matched_points"] for r in data["rows"]] == [2, 2]
    assert data["rows"][0]["stale_readings"] == 1
    assert data["rows"][0]["working_microseconds"] == 200_000_000
    assert data["latest"]["used_percent"] == 3


def test_conflicting_snapshot_breaks_attribution() -> None:
    data = run_report(
        ledger_with_work(), [reading(0, 10), reading(200, 11), reading(200, 12), reading(400, 13)]
    )
    assert sum(r["matched_points"] for r in data["rows"]) == 0
    assert "conflicting_quota_observation" in data["quality"]


@pytest.mark.parametrize(
    "moment", [datetime(2026, 11, 1, 4, tzinfo=UTC), datetime(2026, 1, 1, 5, tzinfo=UTC)]
)
def test_calendar_boundaries_do_not_prorate_quota(moment: datetime) -> None:
    from codex_time.burn import burn_report
    from codex_time.models import QuotaObservation

    ledger = ledger_with_work()
    ledger.quota_observations = [
        QuotaObservation(**{**reading(0, 10), "at": moment - timedelta(seconds=60)}),
        QuotaObservation(**{**reading(0, 12), "at": moment + timedelta(seconds=60)}),
    ]
    for period in ("day", "week", "month"):
        data = burn_report(
            ledger,
            period=period,
            selected_date=moment.astimezone(
                __import__("zoneinfo").ZoneInfo("America/Toronto")
            ).date(),
        )
        assert sum(r["matched_points"] for r in data["rows"]) == 0
        assert sum(r["excluded_boundary_points"] for r in data["rows"]) == 2


def test_toronto_dst_uses_elapsed_time_and_unknown_mix() -> None:
    from codex_time.burn import burn_report
    from codex_time.models import QuotaObservation

    ledger = ledger_with_work()
    turn = ledger.sessions["0"].turns["turn"]
    turn.end = None
    turn.start = datetime(2026, 11, 1, 5, 55, tzinfo=UTC)
    turn.end = turn.start + timedelta(seconds=600)
    turn.model_contexts = []
    ledger.quota_observations = [
        QuotaObservation(**{**reading(0, 10), "at": turn.start}),
        QuotaObservation(**{**reading(0, 11), "at": turn.end}),
    ]
    data = burn_report(ledger, period="day", selected_date=date(2026, 11, 1))
    assert data["rows"][0]["points_per_working_hour"] == 6
    assert data["rows"][0]["mix"][0]["model_id"] is None


def test_table_csv_and_json_share_values_and_bucket_filtering() -> None:
    from codex_time.burn_output import burn_csv, burn_table

    data = run_report(
        ledger_with_work(),
        [
            reading(0, 10),
            reading(600, 12),
            {**reading(0, 10), "window_minutes": 300, "bucket": "secondary"},
            {**reading(600, 20), "window_minutes": 300, "bucket": "secondary"},
        ],
    )
    assert data["rows"][0]["points_per_working_hour"] == 12
    exported = list(csv.DictReader(io.StringIO(burn_csv(data))))
    assert float(exported[0]["points_per_working_hour"]) == 12
    assert json.loads(exported[0]["mix"]) == data["rows"][0]["mix"]
    assert "12.00" in burn_table(data) and "low confidence" in burn_table(data)
    other = run_report(ledger_with_work(), [reading(0, 10), reading(600, 12)], window_minutes=300)
    assert other["rows"] == [] and other["latest"] is None


def test_quota_ingestion_upgrade_privacy_archive_restart_incremental(tmp_path: Path) -> None:
    from codex_time.models import QuotaObservation

    path = tmp_path / "home/sessions/rollout.jsonl"
    path.parent.mkdir(parents=True)

    def event(at: datetime, used: object, secondary: object = None) -> str:
        return (
            json.dumps(
                {
                    "timestamp": at.isoformat(),
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {"SECRET": "PROMPT"},
                        "rate_limits": {
                            "limit_id": "codex",
                            "plan_type": "pro",
                            "credits": "CREDENTIAL",
                            "primary": dict(
                                used_percent=used, window_minutes=10080, resets_at=1791760139
                            ),
                            "secondary": secondary,
                        },
                    },
                }
            )
            + "\n"
        )

    path.write_text(
        event(BASE, 10, dict(used_percent=20, window_minutes=300, resets_at=1791760139))
    )
    old = ledger_with_work().model_dump(mode="json")
    old["version"] = 2
    old.pop("quota_observations", None)
    ledger = Ledger.model_validate(old)
    assert ledger.version == 3
    stat = path.stat()
    cache = {"version": 2, "files": {f"{stat.st_dev}:{stat.st_ino}": {"offset": stat.st_size}}}
    reader = RolloutReader(tmp_path / "home", cache)
    reader.scan(ledger)
    assert len(ledger.quota_observations) == 2 and reader.checkpoints["version"] == 3
    before = ledger.model_dump_json()
    reader.scan(ledger)
    assert ledger.model_dump_json() == before
    with path.open("a") as out:
        out.write(event(BASE + timedelta(seconds=60), 11))
        out.write(event(BASE + timedelta(seconds=90), "SECRET"))
    archive = tmp_path / "home/archived_sessions"
    archive.mkdir()
    path.rename(archive / path.name)
    RolloutReader(tmp_path / "home", reader.checkpoints).scan(ledger)
    assert len(ledger.quota_observations) == 3
    store = Store(tmp_path / "data", tmp_path / "runtime")
    with store.writer():
        store.save(ledger)
    reloaded = store.load()
    RolloutReader(tmp_path / "home").scan(reloaded)
    assert reloaded == ledger and "SECRET" not in ledger.model_dump_json()
    assert "CREDENTIAL" not in ledger.model_dump_json()
    with pytest.raises(ValidationError):
        QuotaObservation(**reading(0, float("nan")))
    with pytest.raises(ValidationError):
        QuotaObservation(**reading(0, 101))


def test_old_cohort_cannot_bridge_manual_reset_or_replace_latest() -> None:
    data = run_report(
        ledger_with_work(),
        [
            reading(0, 10),
            reading(100, 0, reset=1791846539),
            reading(200, 1, reset=1791846539),
            reading(300, 11),
        ],
    )
    assert sum(r["matched_points"] for r in data["rows"]) == 1
    assert sum(r["working_microseconds"] for r in data["rows"]) == 100_000_000
    assert data["latest"]["resets_at"] == 1791846539
    assert data["latest"]["used_percent"] == 1


def test_latest_does_not_report_stale_optimistic_remaining() -> None:
    data = run_report(ledger_with_work(), [reading(0, 10), reading(100, 11), reading(200, 10)])
    assert data["latest"]["used_percent"] == 11
    assert datetime.fromisoformat(data["latest"]["at"]) == BASE + timedelta(seconds=100)


def test_overlapping_turn_latest_start_owns_mix_without_refilling_wait() -> None:
    ledger = ledger_with_work()
    older = ledger.sessions["0"].turns["turn"]
    older.waits = [Span(start=BASE + timedelta(seconds=100), end=BASE + timedelta(seconds=200))]
    ledger.sessions["0"].turns["new"] = Turn(
        id="new",
        cwd="/other",
        start=BASE + timedelta(seconds=50),
        end=BASE + timedelta(seconds=400),
        model_contexts=[
            ModelContext(at=BASE + timedelta(seconds=50), model_id="B", reasoning_level="max")
        ],
    )
    row = run_report(ledger, [reading(0, 10), reading(600, 12)])["rows"][0]
    assert row["working_microseconds"] == 500_000_000
    assert {m["model_id"]: m["working_microseconds"] for m in row["mix"]} == {
        "A": 250_000_000,
        "B": 250_000_000,
    }


def test_actual_cli_json_csv_and_table_replay_same_saved_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from codex_time.cli import main
    from codex_time.models import QuotaObservation

    ledger = ledger_with_work()
    ledger.quota_observations = [
        QuotaObservation(**reading(0, 10)),
        QuotaObservation(**reading(600, 12)),
    ]
    store = Store(tmp_path / "data", tmp_path / "runtime")
    with store.writer():
        store.save(ledger)
    base = [
        "codex-time",
        "--data-dir",
        str(store.root),
        "--state-dir",
        str(store.runtime),
        "burn",
        "day",
        "--date",
        "2026-10-06",
    ]
    before = (store.root / "ledger.json").read_bytes()
    monkeypatch.setattr("sys.argv", [*base, "--json"])
    assert main() == 0
    data = json.loads(capsys.readouterr().out)
    monkeypatch.setattr("sys.argv", [*base, "--csv"])
    assert main() == 0
    rows = list(csv.DictReader(io.StringIO(capsys.readouterr().out)))
    assert float(rows[0]["matched_points"]) == data["rows"][0]["matched_points"]
    assert int(rows[0]["working_microseconds"]) == data["rows"][0]["working_microseconds"]
    monkeypatch.setattr("sys.argv", base)
    assert main() == 0 and "12.00" in capsys.readouterr().out
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr("sys.argv", [*base, "--color", "always"])
    assert main() == 0 and "\x1b[" in capsys.readouterr().out
    monkeypatch.setattr("sys.argv", [*base, "--plain", "--details", "--color", "always"])
    assert main() == 0
    plain = capsys.readouterr().out
    assert plain.isascii() and "\x1b" not in plain and "historical_upper_bound" in plain
    monkeypatch.setattr("sys.argv", [*base, "--json", "--color", "always"])
    assert main() == 0
    exported = capsys.readouterr().out
    assert "\x1b" not in exported and json.loads(exported) == data
    monkeypatch.setattr("sys.argv", [*base, "--max-gap-seconds", "0"])
    assert main() == 2 and "must be positive" in capsys.readouterr().err
    assert (store.root / "ledger.json").read_bytes() == before


def test_same_timestamp_reset_conflict_never_selects_baseline_by_sort_order() -> None:
    data = run_report(
        ledger_with_work(),
        [
            reading(0, 10),
            reading(100, 11),
            reading(100, 0, reset=1791846539),
            reading(200, 12),
            reading(300, 1, reset=1791846539),
        ],
    )
    assert sum(r["matched_points"] for r in data["rows"]) == 0
    assert sum(r["working_microseconds"] for r in data["rows"]) == 0
    assert "conflicting_quota_observation" in data["quality"]


def test_incremental_reader_does_not_reserialize_saved_quota_on_every_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from codex_time.models import QuotaObservation

    ledger = Ledger(quota_observations=[QuotaObservation(**reading(0, 10))])
    reader = RolloutReader(tmp_path)
    reader.scan(ledger)

    def forbid_repeat_serialization(*args: object, **kwargs: object) -> str:
        raise AssertionError("incremental ingestion must retain its quota evidence index")

    monkeypatch.setattr(QuotaObservation, "model_dump_json", forbid_repeat_serialization)
    reader.scan(ledger)
