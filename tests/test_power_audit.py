"""Synthetic macOS log excerpts, not real uptime evidence."""
from datetime import datetime, timezone
import json
import pytest
from cash_cow.paper.power_audit import audit

START=datetime(2026,11,16,14,30,tzinfo=timezone.utc)
END=datetime(2026,11,16,21,tzinfo=timezone.utc)
NOW=datetime(2026,11,17,8,tzinfo=timezone.utc)


def test_midnight_timezone_and_partial_wakes_are_preserved_without_private_text():
    raw=b"""2026-11-16 22:07:25 +0800 Sleep               Entering Sleep state due to 'Clamshell Sleep':PRIVATE Using Batt
2026-11-16 22:30:01 +0800 Wake Requests       PRIVATE
2026-11-16 22:30:02 +0800 Assertions          PRIVATE PreventUserIdleSystemSleep
2026-11-16 23:30:00 +0800 DarkWake            PRIVATE Using BATT
2026-11-17 00:00:00 +0800 Sleep               Entering Sleep state due to 'Maintenance Sleep':PRIVATE Using BATT
2026-11-17 04:59:00 +0800 Wake                PRIVATE Using AC
2026-11-17 05:00:00 +0800 Sleep               Entering Sleep state due to 'PRIVATE': Using BATT
"""
    result=audit(raw,START,END,NOW)
    assert result['status']=='observations_available'
    assert result['last_transition_before_window']['reason']=='clamshell'
    assert result['transition_counts']=={'DarkWake':1,'Sleep':1,'Wake':1}
    assert result['sleep_reason_counts']=={'maintenance':1}
    assert result['transitions'][0]['at']=='2026-11-16T15:30:00+00:00'
    assert result['transitions'][0]['power_source']=='battery'
    assert result['transitions'][-1]['power_source']=='ac'
    assert 'PRIVATE' not in json.dumps(result)


def test_empty_or_irrelevant_log_never_claims_healthy_uptime():
    result=audit(b'no sleep records',START,END,NOW)
    assert result['status']=='review_required'
    assert result['issues']==['no_transitions_in_window']
    assert result['last_transition_before_window'] is None


def test_corrupt_chronology_and_unfamiliar_reasons_are_sanitized():
    raw=b"""2026-11-17 04:59:00 +0800 Wake                PRIVATE
2026-11-16 23:00:00 +0800 Sleep               Entering Sleep state due to 'PRIVATE': Using Batt
2026-11-99 23:00:00 +0800 Wake                PRIVATE
2026-11-18 23:00:00 +0800 Wake                PRIVATE
"""
    result=audit(raw,START,END,NOW)
    assert set(result['issues'])=={'nonmonotonic_transitions','invalid_transition_timestamp','future_transition'}
    assert result['sleep_reason_counts']=={'other':1}
    assert 'PRIVATE' not in json.dumps(result)


@pytest.mark.parametrize('start,end', [(END,START),(START,NOW.replace(day=18)),(START.replace(tzinfo=None),END)])
def test_invalid_interval_is_rejected(start,end):
    with pytest.raises(ValueError):audit(b'',start,end,NOW)


def test_invalid_encoding_is_not_empty_success():
    assert 'invalid_log_encoding' in audit(b'\xff',START,END,NOW)['issues']
