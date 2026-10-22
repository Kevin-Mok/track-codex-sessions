"""Human detail reports stay useful without dumping the machine evidence."""

import copy
from collections import Counter

import pytest
from rich.cells import cell_len
from test_token_reports import DAY, fixture

from codex_time.day_output import day_table
from codex_time.overview import overview_report
from codex_time.overview_output import overview_table
from codex_time.reporting import daily_report


@pytest.mark.parametrize("width", [48, 88, 120])
def test_projects_details_keep_breakdown_without_catalog_or_repeated_titles(width):
    data = daily_report(fixture(), selected_date=DAY)
    data["diagnostics"] = [f"internal notice {index}" for index in range(100)]
    before = copy.deepcopy(data)
    output = day_table(data, width=width, details=True, plain=True)
    compact = "".join(output.split())
    assert "Pricingmodels:" not in compact and "FXlast_" not in compact
    assert "ExactUSD:" not in compact and "Usage:" not in output
    assert "Input:" in output and "Output:" in output and "Cached:" in output
    assert "100 recording notices" in output
    assert "--json" in output and "internal notice" not in output
    assert "root" in output and "gpt-4.1" in compact and "internal-unpriced" in compact
    titles = Counter(
        "".join(session["title"].split()) or "Untitledsession"
        for directory in data["directories"]
        for session in directory["sessions"]
    )
    for title, count in titles.items():
        assert compact.count(title) == count
    assert all(cell_len(line) <= width for line in output.splitlines())
    assert len(output.splitlines()) < (125 if width == 48 else 85)
    assert output.isascii() and "\x1b" not in output
    assert data == before


def test_overview_details_do_not_dump_catalog_or_every_child_identity():
    data = overview_report(fixture(), selected_date=DAY)
    before = copy.deepcopy(data)
    output = overview_table(data, width=88, details=True, plain=True)
    assert "Pricing models:" not in output and "FX last_" not in output
    assert "Exact USD:" not in output and "Child contribution:" not in output
    assert "Input:" in output and "Output:" in output
    assert "--json" in output
    assert len(output.splitlines()) < 100
    assert data == before


def test_provenance_does_not_grow_with_catalog_size():
    from codex_time.token_output import provenance

    lines = []
    provenance(
        lambda value, style: lines.append(value),
        {"version": "catalog-v1", "verified_on": "2026-10-06", "models": {"x": "y"}},
        {"rate": "1.35", "observation_date": "2026-10-06", "age_days": 1},
        details=True,
    )
    assert len(lines) <= 3
    assert "1 day old" in " ".join(lines)
    assert "catalog-v1" in " ".join(lines)
    assert not any("models:" in line for line in lines)
