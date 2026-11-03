from copy import deepcopy
from datetime import date
import json
import subprocess

import pytest

from cash_cow.daily_report import commits_for_day, load_performance, render_report, research_status


@pytest.fixture
def observations():
    return {"mode": "paper", "strategy_id": "frozen_v1", "sessions": [
        {"session_date": "2026-10-30", "opening_nav": 2000, "closing_nav": 2020, "external_flow": 0, "fees": 2},
        {"session_date": "2026-11-02", "opening_nav": 2020, "closing_nav": 1980, "external_flow": 0, "fees": 3},
    ]}


def load(tmp_path, observations):
    path = tmp_path / "sessions.json"
    path.write_text(json.dumps(observations))
    return load_performance(path, date(2026, 11, 3))


def test_nav_returns_do_not_deduct_fees_twice(tmp_path, observations):
    result = load(tmp_path, observations)
    assert result["observed_net_pnl"] == -20
    assert result["observed_return"] == pytest.approx(-0.01)
    assert result["session_close_drawdown"] == pytest.approx(1980 / 2020 - 1)
    assert result["fees_already_in_nav"] == 5
    assert result["observed_monthly_returns"]["2026-10"] == pytest.approx(0.01)
    assert len(result["sha256"]) == 64


@pytest.mark.parametrize("field,value", [
    ("external_flow", 100), ("closing_nav", float("nan")),
    ("closing_nav", float("inf")), ("opening_nav", True),
    ("closing_nav", 0), ("fees", -1),
    ("opening_nav", 2019), ("session_date", "2026-10-30"),
    ("session_date", "2026-11-04"),
])
def test_invalid_telemetry_fails_closed(tmp_path, observations, field, value):
    observations["sessions"][1][field] = value
    with pytest.raises(ValueError):
        load(tmp_path, observations)


def test_mode_is_required(tmp_path, observations):
    del observations["mode"]
    with pytest.raises(ValueError):
        load(tmp_path, observations)


def test_source_hash_changes_with_evidence(tmp_path, observations):
    original = load(tmp_path, observations)
    changed = deepcopy(observations)
    changed["sessions"][-1]["closing_nav"] += 1
    assert load(tmp_path, changed)["sha256"] != original["sha256"]


def test_model_cost_basis_is_preserved(tmp_path, observations):
    observations["cost_basis"] = "Modeled commissions and slippage; not broker fees"
    assert load(tmp_path, observations)["cost_basis"] == observations["cost_basis"]


def test_git_day_uses_singapore_committer_date(tmp_path):
    import os
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    env = dict(os.environ, GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="test@example.com",
               GIT_COMMITTER_NAME="Test", GIT_COMMITTER_EMAIL="test@example.com",
               GIT_AUTHOR_DATE="2026-11-02T12:00:00Z", GIT_COMMITTER_DATE="2026-11-02T17:00:00Z")
    subprocess.run(["git", "-C", str(tmp_path), "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-qm", "Fixture"], check=True, env=env)
    assert not commits_for_day(tmp_path, date(2026, 11, 2))
    assert len(commits_for_day(tmp_path, date(2026, 11, 3))) == 1
    report = render_report(tmp_path, date(2026, 11, 3))
    assert "No paper/live session telemetry was supplied" in report
    assert "PENDING" in report


def test_research_pointer_cannot_escape_repo(tmp_path):
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports/LATEST_V3.txt").write_text("../../secrets")
    with pytest.raises(ValueError):
        research_status(tmp_path)
