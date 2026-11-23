from copy import deepcopy

import pytest

from cash_cow.intraday.halt_audit import classify_gaps


def gap(start='2020-03-09T09:34:00-04:00', end='2020-03-09T09:51:00-04:00', minutes=17):
    return {'start': start, 'end_exclusive': end, 'minutes': minutes}


def test_partial_trigger_and_reopen_minutes_remain_distinct_and_inputs_unchanged():
    gaps = [gap()]
    halts = [{'start': '2020-03-09T13:34:13Z', 'end_exclusive': '2020-03-09T13:49:13Z'}]
    before = deepcopy((gaps, halts))
    result = classify_gaps(gaps, halts)
    assert result['counts'] == {'fully_contained': 14, 'partially_overlapping': 2, 'outside_known_halts': 1}
    assert result['missing_minutes'] == 17
    assert (gaps, halts) == before


def test_half_open_boundaries_and_adjacent_halts_do_not_double_count():
    gaps = [gap(end='2020-03-09T09:37:00-04:00', minutes=3)]
    halts = [{'start': '2020-03-09T09:35:00-04:00', 'end_exclusive': '2020-03-09T09:35:30-04:00'},
             {'start': '2020-03-09T09:35:30-04:00', 'end_exclusive': '2020-03-09T09:36:00-04:00'}]
    assert classify_gaps(gaps, halts)['counts'] == {
        'fully_contained': 1, 'partially_overlapping': 0, 'outside_known_halts': 2}


@pytest.mark.parametrize('bad', [
    gap(start='2020-03-09T09:34:00'), gap(start='NaT'),
    gap(start='2020-03-09T09:34:01-04:00'), gap(minutes=16), gap(minutes=True),
    gap(end='2020-03-09T09:34:00-04:00'),
])
def test_invalid_gap_evidence_is_rejected(bad):
    with pytest.raises(ValueError):
        classify_gaps([bad], [])


def test_unsorted_or_overlapping_evidence_is_rejected():
    with pytest.raises(ValueError, match='ordered and nonoverlapping'):
        classify_gaps([gap(), gap()], [])
    with pytest.raises(ValueError, match='ordered and nonoverlapping'):
        classify_gaps([gap()], [gap(), gap()])


def test_no_known_halt_is_not_proof_of_tradability():
    assert classify_gaps([gap()], [])['counts']['outside_known_halts'] == 17
    assert classify_gaps([], [])['missing_minutes'] == 0


def test_cli_keeps_original_failure_even_when_all_gaps_overlap(tmp_path, monkeypatch, capsys):
    import json
    from cash_cow.intraday import halt_audit
    from cash_cow.data import sha256
    diagnostic = {'status': 'review_required', 'issues': ['missing_regular_minutes'],
                  'missing_intervals': [gap()], 'source_sha256': {'synthetic.csv': 'test'}}
    monkeypatch.setattr(halt_audit, 'audit_cache', lambda root: deepcopy(diagnostic))
    path = tmp_path/'configs/historical_mwcb_2020.json'
    path.parent.mkdir()
    path.write_text(json.dumps({'source': 'https://example.test/synthetic', 'published': '2021-03-31',
                                'halts': [gap()]}))
    result = halt_audit.audit_halts(tmp_path)
    assert result['counts']['fully_contained'] == 17
    assert result['status'] == 'review_required'
    assert result['input_source_sha256'] == diagnostic['source_sha256']
    assert result['halt_reference_sha256'] == sha256(path)
    monkeypatch.setattr(halt_audit, 'audit_halts', lambda: result)
    assert halt_audit.main() == 2
    assert json.loads(capsys.readouterr().out)['unchanged_input_issues'] == ['missing_regular_minutes']
