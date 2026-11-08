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


def coverage_files(tmp_path, observations):
    observations['strategy_id'] = 'frozen_v1_cost_stress'
    state = {'sessions': {r['session_date']: {
        'opening_stress_nav': r['opening_nav'], 'closing_stress_nav': r['closing_nav'],
        'modeled_costs': r['fees'], 'closed': True, 'partial_attendance': False,
        'blocked': None,
    } for r in observations['sessions']}}
    p, s = tmp_path/'sessions.json', tmp_path/'state.json'
    p.write_text(json.dumps(observations)); s.write_text(json.dumps(state))
    return p, s, state


def test_missing_coverage_is_unverified_even_for_flat_returns(tmp_path, observations):
    result = load(tmp_path, observations)
    assert result['coverage']['counts'] == {'unverified': 2}
    assert result['coverage']['state_sha256'] is None


@pytest.mark.parametrize('flags', [
    {'blocked': 'private-reason'}, {'partial_attendance': True},
    {'closed': False}, {'unresolved_at_close': True},
])
def test_incomplete_loss_retained_and_reason_sanitized(tmp_path, observations, flags):
    p, s, state = coverage_files(tmp_path, observations)
    state['sessions']['2026-11-02'].update(flags); s.write_text(json.dumps(state))
    before = (p.read_bytes(), s.read_bytes())
    result = load_performance(p, date(2026,11,3), s)
    assert result['coverage']['counts'] == {'no_local_block_recorded': 1, 'incomplete': 1}
    assert result['observed_net_pnl'] == -20
    assert result['sessions'] == 2
    assert 'private-reason' not in json.dumps(result)
    assert before == (p.read_bytes(), s.read_bytes())


@pytest.mark.parametrize('field,value', [
    ('opening_stress_nav', 999), ('closing_stress_nav', float('nan')),
    ('modeled_costs', True), ('closed', 'false'), ('partial_attendance', None),
    ('unresolved_at_close', 1), ('blocked', []),
])
def test_mismatched_or_malformed_coverage_fails_closed(tmp_path, observations, field, value):
    p, s, state = coverage_files(tmp_path, observations)
    state['sessions']['2026-11-02'][field] = value; s.write_text(json.dumps(state))
    with pytest.raises(ValueError):
        load_performance(p, date(2026,11,3), s)


def test_missing_session_cannot_be_silently_dropped(tmp_path, observations):
    p, s, state = coverage_files(tmp_path, observations)
    del state['sessions']['2026-11-02']; s.write_text(json.dumps(state))
    with pytest.raises(ValueError, match='missing'):
        load_performance(p, date(2026,11,3), s)


def test_live_source_cannot_be_joined_to_paper_state(tmp_path, observations):
    p, s, state = coverage_files(tmp_path, observations)
    observations['mode'] = 'live'; p.write_text(json.dumps(observations))
    with pytest.raises(ValueError, match='paper cost-stress'):
        load_performance(p, date(2026,11,3), s)


def test_rendered_report_exposes_incomplete_sessions(tmp_path, observations, monkeypatch):
    import cash_cow.daily_report as module
    monkeypatch.setattr(module, 'commits_for_day', lambda *_: [])
    monkeypatch.setattr(module, 'git', lambda *_: 'fixture')
    p, s, state = coverage_files(tmp_path, observations)
    state['sessions']['2026-11-02']['blocked'] = 'monitoring_gap'; s.write_text(json.dumps(state))
    report = render_report(tmp_path, date(2026,11,3), load_performance(p, date(2026,11,3), s))
    assert '| 2026-11-02 | incomplete |' in report
    assert 'Observed net P&L: -20.00' in report
    assert 'Full-month statistics remain unavailable' in report
    unknown = render_report(tmp_path, date(2026,11,3), load_performance(p, date(2026,11,3)))
    assert 'every observed session is **unverified**' in unknown
