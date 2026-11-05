from datetime import datetime, timedelta, timezone
import hashlib
import json

from cash_cow.paper.news_audit import audit_news

NOW=datetime(2026,11,5,8,tzinfo=timezone.utc)


def revision(folder, observed=NOW, updated=None, headline='private headline'):
    m={'id':'private-id','headline':headline,'created_at':(NOW-timedelta(hours=1)).isoformat(),
       'updated_at':(updated or NOW).isoformat()}
    digest=hashlib.sha256(json.dumps(m,sort_keys=True).encode()).hexdigest()
    p=folder/(digest+'.json')
    p.write_text(json.dumps({'first_observed_at':observed.isoformat(),'metadata':m,'sha256':digest}))
    return p


def test_revision_cutoff_prevents_future_revision_leakage(tmp_path):
    revision(tmp_path)
    revision(tmp_path,NOW+timedelta(minutes=1),NOW+timedelta(minutes=1),'future private headline')
    old=audit_news(tmp_path,NOW); new=audit_news(tmp_path,NOW+timedelta(minutes=2))
    assert old['valid_revisions']==1 and old['excluded_observed_after_cutoff']==1
    assert new['valid_revisions']==2 and new['articles_with_multiple_revisions']==1
    assert 'private' not in json.dumps(new)


def test_content_tampering_is_detected_without_repair(tmp_path):
    p=revision(tmp_path); r=json.loads(p.read_text());r['metadata']['headline']='changed';p.write_text(json.dumps(r))
    before=p.read_bytes();result=audit_news(tmp_path,NOW)
    assert result['errors']['revision_hash_mismatch']==1
    assert p.read_bytes()==before


def test_backdated_observation_is_rejected(tmp_path):
    revision(tmp_path,observed=NOW-timedelta(seconds=1))
    assert audit_news(tmp_path,NOW)['errors']['invalid_causal_timestamps']==1


def test_bad_json_and_missing_archive_are_not_silent_success(tmp_path):
    (tmp_path/'broken.json').write_text('{')
    assert audit_news(tmp_path,NOW)['errors']['unreadable_or_invalid_record']==1
    assert audit_news(tmp_path/'absent',NOW)['errors']['missing_archive']==1
