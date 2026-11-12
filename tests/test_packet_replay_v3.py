from copy import deepcopy
import json

from cash_cow.packet_research.capture import save_capture
from cash_cow.packet_research.replay_v3 import audit_packets
from test_receipt_history import fixture


def archive(folder):
    (folder/'ai_decisions').mkdir();(folder/'captures').mkdir()
    capture, context = fixture();context['news'] = 'PRIVATE_LICENSED_HEADLINE'
    (folder/'ai_decisions/a.json').write_text(json.dumps({'status': 'completed', 'context': context}))
    save_capture(capture, folder/'captures')
    return capture, context


def test_archive_is_read_only_aggregate_and_all_arms_pass(tmp_path):
    archive(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.rglob('*.json')}
    result = audit_packets(tmp_path, tmp_path/'captures')
    assert result['status'] == 'construction_checks_passed'
    assert all(a['assembled'] == 1 for a in result['arms'].values())
    assert 'PRIVATE_' not in json.dumps(result)
    assert before == {p: p.read_bytes() for p in before}


def test_future_and_failed_decisions_remain_in_denominator(tmp_path):
    _, context = archive(tmp_path);context['as_of'] = '2026-11-12T15:04:59Z'
    (tmp_path/'ai_decisions/b.json').write_text(json.dumps({'status': 'failed', 'context': context}))
    result = audit_packets(tmp_path, tmp_path/'captures')
    assert result['decision_records'] == 2 and result['decision_statuses']['failed'] == 1
    assert result['arms']['baseline']['assembled'] == 2
    assert result['arms']['history']['reasons'] == {'no_capture_before_cutoff': 1}


def test_equal_time_ambiguity_does_not_choose_convenient_capture(tmp_path):
    capture, _ = archive(tmp_path);capture['status'] = 'incomplete_bars'
    save_capture(capture, tmp_path/'captures')
    result = audit_packets(tmp_path, tmp_path/'captures')
    assert result['arms']['history']['reasons'] == {'ambiguous_latest_capture': 1}


def test_latest_incomplete_capture_does_not_fall_back(tmp_path):
    capture, _ = archive(tmp_path);capture['status'] = 'incomplete_bars'
    capture['bars']['received_at'] = '2026-11-12T15:05:01Z'
    save_capture(capture, tmp_path/'captures')
    result = audit_packets(tmp_path, tmp_path/'captures')
    assert result['capture_statuses'] == {'captured': 1, 'incomplete_bars': 1}
    assert result['arms']['history']['reasons'] == {'packet_validation_failed': 1}


def test_tampered_capture_or_bad_filename_fails_history_archive(tmp_path):
    capture, _ = archive(tmp_path)
    (tmp_path/'captures/wrong.json').write_text(json.dumps(capture))
    result = audit_packets(tmp_path, tmp_path/'captures')
    assert result['archive_errors'] == {'invalid_capture': 1}
    assert result['arms']['baseline']['assembled'] == 1
    assert result['arms']['history']['reasons'] == {'invalid_capture_archive': 1}


def test_invalid_decisions_and_missing_release_pair_are_retained(tmp_path):
    archive(tmp_path);(tmp_path/'ai_decisions/b.json').write_text('PRIVATE_BAD_JSON')
    result = audit_packets(tmp_path, tmp_path/'captures', release_path=tmp_path/'missing.json')
    assert result['decision_records'] == 2
    assert result['arms']['history_and_releases']['rejected'] == 2
    assert result['arms']['baseline']['rejected'] == 1
    assert 'PRIVATE_' not in json.dumps(result)


def test_empty_archive_never_passes(tmp_path):
    result = audit_packets(tmp_path, tmp_path/'captures')
    assert result['status'] == 'review_required'
    assert result['archive_errors'] == {'missing_decisions': 1, 'missing_captures': 1}


def test_concurrent_source_changes_are_reported(tmp_path, monkeypatch):
    import cash_cow.packet_research.replay_v3 as module
    archive(tmp_path);original = module.build_packet
    def change(*args, **kwargs):
        result = original(*args, **kwargs)
        (tmp_path/'ai_decisions/a.json').write_text('changed')
        return result
    monkeypatch.setattr(module, 'build_packet', change)
    result = audit_packets(tmp_path, tmp_path/'captures')
    assert result['archive_errors']['source_changed_during_audit'] == 1
