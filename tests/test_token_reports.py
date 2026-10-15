"""Token accounting and cost reports conserve evidence through every grouping."""

import json
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from rich.cells import cell_len

from codex_time.cli import main, parser
from codex_time.models import Ledger, ModelContext, Session, Turn

BASE = datetime(2026, 10, 6, 16, tzinfo=UTC)
DAY = date(2026, 10, 6)


def usage(sid, ident, amount, *, cwd="/old", model="gpt-4.1", at=BASE):
    from codex_time.models import TokenCounts, UsageObservation

    counts = TokenCounts(
        input_tokens=amount,
        cached_input_tokens=0,
        cache_write_input_tokens=0,
        output_tokens=0,
        reasoning_output_tokens=0,
        total_tokens=amount,
    )
    return UsageObservation(
        id=ident,
        session_id=sid,
        at=at,
        cwd=cwd,
        model_id=model,
        cumulative=counts,
        delta=counts,
        last_usage=counts,
        request_input_tokens=amount,
    )


def fixture():
    root = Session(
        id="root",
        title="Root task",
        cwd="/latest",
        created=BASE,
        updated=BASE,
        turns={
            "t": Turn(
                id="t",
                cwd="/old",
                start=BASE,
                end=BASE + timedelta(seconds=60),
                model_contexts=[ModelContext(at=BASE, model_id="gpt-4.1")],
            )
        },
    )
    child = Session(
        id="child", cwd="/child", created=BASE, updated=BASE, parent_id="root", is_child=True
    )
    grandchild = child.model_copy(update={"id": "grandchild", "parent_id": "child"})
    orphan = child.model_copy(update={"id": "orphan", "parent_id": "missing"})
    fork = Session(id="fork", cwd="/old", created=BASE, updated=BASE, archived=True)
    ledger = Ledger(sessions={s.id: s for s in [root, child, grandchild, orphan, fork]})
    ledger.usage_observations = [
        usage("root", "r", 100),
        usage("child", "c", 200, cwd="/child"),
        usage("grandchild", "g", 300, model="internal-unpriced"),
        usage("orphan", "o", 400, cwd="/lost", model=None),
        usage("fork", "f", 500),
        usage("root", "later", 600, cwd="/new", model="internal-unpriced"),
    ]
    return ledger


def test_parser_periods_defaults_and_aliases():
    for name in ["overview", "projects", "day"]:
        assert parser().parse_args([name]).period == "day"
        for period in ["day", "week", "month", "all"]:
            assert parser().parse_args([name, period]).period == period


def test_project_groups_conserve_tokens_and_costs_without_child_time():
    from codex_time.reporting import daily_report

    ledger = fixture()
    before = ledger.model_dump_json()
    data = daily_report(ledger, selected_date=DAY)
    assert data["total_seconds"] == 60
    assert data["usage"]["tokens"]["total_tokens"] == 2100
    assert data["usage"]["unpriced_tokens"] == 1300
    assert data["usage"]["cost_complete"] is False
    assert data["usage"]["cad"] is None
    assert sum(d["usage"]["tokens"]["total_tokens"] for d in data["directories"]) == 2100
    assert sum(Decimal(d["usage"]["usd"]) for d in data["directories"]) == Decimal(
        data["usage"]["usd"]
    )
    for directory in data["directories"]:
        assert (
            sum(s["usage"]["tokens"]["total_tokens"] for s in directory["sessions"])
            == directory["usage"]["tokens"]["total_tokens"]
        )
        for s in directory["sessions"]:
            assert (
                sum(m["usage"]["tokens"]["total_tokens"] for m in s["models"])
                == s["usage"]["tokens"]["total_tokens"]
            )
    rows = {d["cwd"]: d for d in data["directories"]}
    assert set(rows) == {"/old", "/new", "/child", "/lost"}
    assert rows["/child"]["sessions"][0]["id"] == "root"
    assert rows["/child"]["sessions"][0]["children"][0]["session_id"] == "child"
    assert rows["/lost"]["sessions"][0]["id"] == "orphan"
    assert "orphaned_child" in rows["/lost"]["sessions"][0]["usage"]["diagnostics"]
    assert ledger.model_dump_json() == before


def test_filters_apply_recorded_cwd_root_session_and_root_archive_state():
    from codex_time.reporting import daily_report

    ledger = fixture()
    assert (
        daily_report(ledger, selected_date=DAY, cwd="/child")["usage"]["tokens"]["total_tokens"]
        == 200
    )
    assert daily_report(ledger, selected_date=DAY, cwd="/latest")["directories"] == []
    assert (
        daily_report(ledger, selected_date=DAY, session_id="root")["usage"]["tokens"][
            "total_tokens"
        ]
        == 1200
    )
    assert (
        daily_report(ledger, selected_date=DAY, session_id="child")["usage"]["tokens"][
            "total_tokens"
        ]
        == 200
    )
    assert (
        daily_report(ledger, selected_date=DAY, archive="archived")["usage"]["tokens"][
            "total_tokens"
        ]
        == 500
    )
    assert (
        daily_report(ledger, selected_date=DAY, archive="active")["usage"]["tokens"]["total_tokens"]
        == 1600
    )


def test_observation_date_and_dst_not_elapsed_proportion():
    from codex_time.reporting import daily_report

    ledger = fixture()
    ledger.usage_observations = [
        usage("root", "before", 100, at=datetime(2026, 11, 1, 3, 59, 59, tzinfo=UTC)),
        usage("root", "after", 200, at=datetime(2026, 11, 1, 4, tzinfo=UTC)),
        usage("root", "fold1", 300, at=datetime(2026, 11, 1, 5, 30, tzinfo=UTC)),
        usage("root", "fold2", 400, at=datetime(2026, 11, 1, 6, 30, tzinfo=UTC)),
    ]
    assert (
        daily_report(ledger, selected_date=date(2026, 10, 31))["usage"]["tokens"]["total_tokens"]
        == 100
    )
    assert (
        daily_report(ledger, selected_date=date(2026, 11, 1))["usage"]["tokens"]["total_tokens"]
        == 900
    )
    assert (
        daily_report(ledger, selected_date=date(2026, 11, 1), timezone_name="UTC")["usage"][
            "tokens"
        ]["total_tokens"]
        == 1000
    )


@pytest.mark.parametrize(
    "period,first,last",
    [("week", "2026-10-05", "2026-10-11"), ("month", "2026-10-01", "2026-10-31")],
)
def test_period_consistency(period, first, last):
    from codex_time.overview import overview_report
    from codex_time.reporting import daily_report

    ledger = fixture()
    projects = daily_report(ledger, period=period, selected_date=DAY)
    overview = overview_report(ledger, period=period, selected_date=DAY)
    assert projects["from"] == first and projects["to"] == last
    assert overview["token_usage"]["from"] == first and overview["token_usage"]["to"] == last
    assert projects["usage"] == overview["token_usage"]["usage"]


def test_all_time_uses_history_and_latest_allowance_without_rate():
    from codex_time.models import QuotaObservation
    from codex_time.overview import overview_report
    from codex_time.overview_output import overview_table

    ledger = fixture()
    ledger.usage_observations.append(usage("root", "old", 10, at=BASE - timedelta(days=400)))
    ledger.quota_observations = [
        QuotaObservation(
            at=BASE,
            limit_id="codex",
            bucket="primary",
            window_minutes=10080,
            resets_at=int((BASE + timedelta(days=1)).timestamp()),
            used_percent=15.0,
        )
    ]
    result = overview_report(ledger, period="all")
    assert result["token_usage"]["usage"]["tokens"]["total_tokens"] == 2110
    assert result["allowance"]["rows"] == []
    assert result["allowance"]["latest"]["used_percent"] == 15
    output = overview_table(result, plain=True)
    assert "All recorded history" in output and "Latest allowance snapshot" in output
    assert "Observed consumption" not in output and "pts / working hour" not in output
    with pytest.raises(ValueError, match="--date"):
        overview_report(ledger, period="all", selected_date=DAY)


def test_unknown_usage_and_true_zero_are_distinct():
    from codex_time.reporting import daily_report

    ledger = fixture()
    ledger.usage_observations = []
    assert daily_report(ledger, selected_date=DAY)["usage"]["status"] == "unavailable"
    ledger.usage_observations = [usage("root", "zero", 0)]
    assert daily_report(ledger, selected_date=DAY)["usage"]["status"] == "recorded"
    assert daily_report(ledger, selected_date=DAY)["usage"]["tokens"]["total_tokens"] == 0
    ledger.usage_observations[0].delta = None
    assert daily_report(ledger, selected_date=DAY)["usage"]["status"] == "partial"
    assert daily_report(ledger, selected_date=DAY)["usage"]["uncertain_observations"] == 1


@pytest.mark.parametrize("width", [20, 32, 48, 88])
def test_rendering_tokens_models_usd_cad_unpriced_and_children(width):
    from codex_time.day_output import day_table
    from codex_time.fx import FXSnapshot
    from codex_time.reporting import daily_report

    data = daily_report(
        fixture(), selected_date=DAY, fx=FXSnapshot(rate=Decimal("1.35"), observation_date=DAY)
    )
    plain = day_table(data, width=width, plain=True)
    details = day_table(data, width=width, plain=True, details=True)
    assert all(cell_len(line) <= width for line in details.splitlines())
    compact = "".join(plain.split())
    assert "USD" in compact and "CAD" in compact and "tokens" in compact
    assert "gpt-4.1" in compact and "internal-unpriced" in compact
    assert "Knownpricedsubtotal" in compact
    assert "Childcontributions" not in compact
    assert "Childcontributions" in "".join(details.split())
    assert "2026-10-06" in compact and plain.isascii() and "\x1b" not in plain


def test_cli_readonly_exports_and_all_date_rejection(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "data"
    root.mkdir()
    (root / "ledger.json").write_text(fixture().model_dump_json())
    state = tmp_path / "state"
    before = (root / "ledger.json").read_bytes()
    for command in ["overview", "projects", "day"]:
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "codex-time",
                "--data-dir",
                str(root),
                "--state-dir",
                str(state),
                command,
                "all",
                "--json",
            ],
        )
        assert main() == 0
        data = json.loads(capsys.readouterr().out)
        summary = data["token_usage"]["usage"] if command == "overview" else data["usage"]
        assert summary["tokens"]["total_tokens"] == 2100
        assert isinstance(summary["usd"], str)
        monkeypatch.setattr(
            sys,
            "argv",
            ["codex-time", "--data-dir", str(root), command, "all", "--date", "2026-10-06"],
        )
        assert main() == 2
        assert "--date" in capsys.readouterr().err
    assert (root / "ledger.json").read_bytes() == before
    assert {p.relative_to(state) for p in state.rglob("*") if p.is_file()} == {
        Path("overview-report.json")
    }
    cache = json.loads((state / "overview-report.json").read_bytes())
    assert cache["version"] == 1
    assert cache["report"]["token_usage"]["usage"]["tokens"]["total_tokens"] == 2100


def test_aggregation_keeps_low_order_money_digits_for_large_exact_counters():
    from codex_time.fx import FXSnapshot
    from codex_time.reporting import daily_report

    ledger = fixture()
    ledger.usage_observations = [usage("root", "huge", 10**40 + 1), usage("root", "small", 1)]
    report = daily_report(
        ledger, selected_date=DAY, fx=FXSnapshot(rate=Decimal("1.35"), observation_date=DAY)
    )
    assert Decimal(report["usage"]["usd"]) == Decimal("2" + "0" * 34 + ".000004")
    assert Decimal(report["usage"]["cad"]) == Decimal("27" + "0" * 33 + ".0000054")


@pytest.mark.parametrize("observed", ["root", "child"])
def test_missing_actual_parent_or_child_usage_stays_incomplete(observed):
    from codex_time.reporting import daily_report

    ledger = fixture()
    ledger.sessions = {sid: ledger.sessions[sid] for sid in ["root", "child"]}
    ledger.sessions["child"].turns = ledger.sessions["root"].model_copy(deep=True).turns
    ledger.usage_observations = [usage(observed, "observed", 100)]
    result = daily_report(ledger, selected_date=DAY)
    assert result["total_seconds"] == 60
    assert result["usage"]["cost_complete"] is False
    assert result["usage"]["unavailable_session_count"] == 1
    assert result["usage"]["status"] == "partial"
    assert "usage_unavailable_for_recorded_work" in result["usage"]["diagnostics"]


def test_all_time_latest_allowance_does_not_depend_on_latest_activity_date():
    from codex_time.models import QuotaObservation
    from codex_time.overview import overview_report

    ledger = fixture()
    ledger.quota_observations = [
        QuotaObservation(
            at=BASE,
            limit_id="codex",
            bucket="primary",
            window_minutes=10080,
            resets_at=int((BASE + timedelta(days=1)).timestamp()),
            used_percent=15.0,
        )
    ]
    ledger.usage_observations.append(usage("root", "future", 100, at=BASE + timedelta(days=1)))
    result = overview_report(ledger, period="all")
    assert result["allowance"]["latest"]["used_percent"] == 15
    assert result["allowance"]["rows"] == []


def test_unpriced_positive_model_never_looks_like_a_free_model():
    from codex_time.reporting import daily_report
    from codex_time.token_output import usage_line

    report = daily_report(fixture(), selected_date=DAY)
    unknown = next(row for row in report["models"] if row["model_id"] == "internal-unpriced")
    assert "USD unpriced" in usage_line(unknown["usage"])
    assert "USD 0.00" not in usage_line(unknown["usage"])


def test_auto_review_is_excluded_from_token_and_cost_totals_but_evidence_survives():
    from codex_time.overview import overview_report
    from codex_time.reporting import daily_report

    ledger = fixture()
    ledger.usage_observations.append(usage("root", "auto", 12345, model="codex-auto-review"))
    before = ledger.model_dump_json()
    projects = daily_report(ledger, selected_date=DAY)
    overview = overview_report(ledger, selected_date=DAY)
    assert projects["usage"]["tokens"]["total_tokens"] == 2100
    assert projects["usage"] == overview["token_usage"]["usage"]
    assert all(row["model_id"] != "codex-auto-review" for row in projects["models"])
    assert all(
        model["model_id"] != "codex-auto-review"
        for directory in projects["directories"]
        for session in directory["sessions"]
        for model in session["models"]
    )
    assert projects["usage"]["unpriced_tokens"] == 1300
    assert projects["excluded_models"] == ["codex-auto-review"]
    assert overview["token_usage"]["excluded_models"] == ["codex-auto-review"]
    assert ledger.model_dump_json() == before


def test_auto_review_only_usage_does_not_become_missing_usage_coverage():
    from codex_time.reporting import daily_report

    ledger = fixture()
    ledger.sessions = {"root": ledger.sessions["root"]}
    ledger.usage_observations = [usage("root", "auto", 12345, model="codex-auto-review")]
    report = daily_report(ledger, selected_date=DAY)
    assert report["usage"]["unavailable_session_count"] == 0
    assert report["usage"]["tokens"]["total_tokens"] is None
    assert report["models"] == []
    assert report["total_seconds"] == 60


def test_auto_review_only_usage_is_labeled_excluded_in_terminal_reports():
    from codex_time.day_output import day_table
    from codex_time.overview import overview_report
    from codex_time.overview_output import overview_table
    from codex_time.reporting import daily_report

    ledger = fixture()
    ledger.sessions = {"root": ledger.sessions["root"]}
    ledger.usage_observations = [usage("root", "auto", 12345, model="codex-auto-review")]
    projects = daily_report(ledger, selected_date=DAY)
    assert projects["usage"]["status"] == "excluded"
    for rendered in [
        day_table(projects, plain=True),
        overview_table(overview_report(ledger, selected_date=DAY), plain=True),
    ]:
        assert "codex-auto-review" in rendered
        assert "Token usage excluded" in rendered
        assert "Run import-history" not in rendered
        assert "USD 0.00" not in rendered
