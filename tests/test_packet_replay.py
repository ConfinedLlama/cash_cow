from copy import deepcopy
import json

from cash_cow.packet_research.replay import audit_packets
from test_packet_history import inputs
from test_packet_releases import release


def archive(folder):
    (folder/'bars').mkdir();(folder/'ai_decisions').mkdir()
    snapshot,context=inputs();context['news']=[{'headline':'private-headline'}]
    (folder/'bars/a.json').write_text(json.dumps(snapshot))
    (folder/'ai_decisions/a.json').write_text(json.dumps({'status':'completed','context':context,'proposal':{'rationale':'private-rationale'}}))
    return snapshot,context


def test_read_only_archive_construction_has_no_raw_data(tmp_path):
    archive(tmp_path)
    before={p:p.read_bytes() for p in tmp_path.rglob('*.json')}
    result=audit_packets(tmp_path)
    assert result['status']=='construction_checks_passed'
    assert all(a['assembled']==1 for a in result['arms'].values())
    assert result['release_availability']['unavailable']==1
    assert 'private-' not in json.dumps(result)
    assert before=={p:p.read_bytes() for p in before}


def test_future_release_is_retained_as_excluded(tmp_path):
    archive(tmp_path);p=tmp_path/'releases.json';p.write_text(json.dumps([release()]))
    result=audit_packets(tmp_path,p)
    assert result['release_availability']=={'unavailable':1,'excluded_future_values':1}


def test_corrupt_snapshot_does_not_silently_pass(tmp_path):
    archive(tmp_path);(tmp_path/'bars/a.json').write_text('private-broken')
    result=audit_packets(tmp_path)
    assert result['status']=='review_required'
    assert result['arms']['baseline']['assembled']==1
    assert result['arms']['history']['rejected']==1
    assert 'private-' not in json.dumps(result)


def test_ambiguous_equal_time_snapshots_do_not_choose_a_convenient_value(tmp_path):
    snapshot,_=archive(tmp_path);other=deepcopy(snapshot);other['bars'][0]['v']+=1
    (tmp_path/'bars/b.json').write_text(json.dumps(other))
    assert audit_packets(tmp_path)['arms']['history']['rejected']==1


def test_later_snapshot_cannot_backfill_an_old_packet(tmp_path):
    snapshot,_=archive(tmp_path);snapshot['observed_at']='2026-11-05T15:05:03Z'
    (tmp_path/'bars/a.json').write_text(json.dumps(snapshot))
    assert audit_packets(tmp_path)['arms']['history']['rejected']==1


def test_failed_records_still_count_and_missing_sources_are_visible(tmp_path):
    _,context=archive(tmp_path)
    (tmp_path/'ai_decisions/b.json').write_text(json.dumps({'status':'failed','context':context}))
    result=audit_packets(tmp_path,tmp_path/'missing.json')
    assert result['records']==2 and result['baseline_record_statuses']['failed']==1
    assert result['arms']['history_and_releases']['rejected']==2
    assert result['archive_errors']['unreadable_release_archive']==1


def test_empty_archive_is_not_a_success(tmp_path):
    result=audit_packets(tmp_path)
    assert result['status']=='review_required' and result['records']==0
