from datetime import datetime, timedelta, timezone
import json
from unittest.mock import Mock

from cash_cow.paper.news import NewsCollector


def test_status_read_error_does_not_kill_collection_loop(tmp_path, monkeypatch, capsys):
    import cash_cow.paper.news as news
    from pathlib import Path
    folder = tmp_path/'news';folder.mkdir()
    status = folder/'status.json';status.write_text('{"last_success":"2026-11-10T15:00:00Z"}')
    original = status.read_bytes()
    class Stop:
        waits = 0
        def is_set(self):return self.waits == 2
        def wait(self, seconds):
            assert seconds == 300
            self.waits += 1
    reads = Path.read_text
    def blocked_read(path, *args, **kwargs):
        if path == status:raise OSError(11, 'private filesystem detail')
        return reads(path, *args, **kwargs)
    collect = Mock(side_effect=[OSError(11, 'private filesystem detail'), None])
    monkeypatch.setattr(Path, 'read_text', blocked_read)
    monkeypatch.setattr(news, 'PaperClient', Mock())
    monkeypatch.setattr(news.NewsCollector, 'collect', collect)
    news.news_worker_loop(tmp_path, Stop())
    assert collect.call_count == 2
    assert status.read_bytes() == original
    out = capsys.readouterr().err
    assert 'error_status_unavailable' in out and 'private' not in out


def test_news_error_keeps_last_success_and_original_revision(tmp_path):
    from cash_cow.paper.news import record_collection_error
    folder = tmp_path/'news';folder.mkdir()
    status = folder/'status.json'
    previous = {'last_success': '2026-11-10T15:00:00Z', 'coverage_gap': True}
    status.write_text(json.dumps(previous))
    revision = folder/'immutable.json';revision.write_text('synthetic revision')
    record_collection_error(tmp_path, ValueError('private article'))
    saved = json.loads(status.read_text())
    assert saved['last_success'] == previous['last_success']
    assert saved['coverage_gap'] is True and saved['error'] == 'ValueError'
    assert revision.read_text() == 'synthetic revision'
    assert 'private' not in status.read_text()


def test_news_error_writer_preserves_corrupt_status(tmp_path, capsys):
    from cash_cow.paper.news import record_collection_error
    folder = tmp_path/'news';folder.mkdir()
    for contents in ('bad-json', '[]'):
        status = folder/'status.json';status.write_text(contents)
        record_collection_error(tmp_path, RuntimeError('private detail'))
        assert status.read_text() == contents
    assert 'private' not in capsys.readouterr().err


def test_news_error_status_write_failure_is_nonfatal(tmp_path, monkeypatch, capsys):
    import cash_cow.paper.news as news
    folder = tmp_path/'news';folder.mkdir()
    status = folder/'status.json';status.write_text('{}')
    monkeypatch.setattr(news, 'atomic_json', Mock(side_effect=OSError('disk unavailable')))
    news.record_collection_error(tmp_path, OSError(11, 'private detail'))
    assert status.read_text() == '{}'
    assert 'error_status_unavailable' in capsys.readouterr().err


def test_unavailable_status_and_diagnostic_sinks_do_not_raise(tmp_path, monkeypatch):
    import cash_cow.paper.news as news
    monkeypatch.setattr(news, 'atomic_json', Mock(side_effect=OSError('disk unavailable')))
    monkeypatch.setattr(news.sys, 'stderr', Mock(write=Mock(side_effect=OSError('sink unavailable'))))
    news.record_collection_error(tmp_path, OSError(11, 'private detail'))


def test_news_revision_keeps_original_first_seen(tmp_path):
    now = datetime(2026, 11, 3, 15, tzinfo=timezone.utc)
    article = {"id": 1, "headline": "Synthetic fixture, not actual news", "created_at": now.isoformat(), "updated_at": now.isoformat()}
    client = Mock()
    client.news_page.return_value = {"news": [article], "next_page_token": None}
    collector = NewsCollector(client, tmp_path)
    assert collector.collect(now)["new_revisions"] == 1
    assert collector.collect(now+timedelta(minutes=5))["new_revisions"] == 0
    article["headline"] = "Revised synthetic fixture"
    article["updated_at"] = (now+timedelta(minutes=6)).isoformat()
    assert collector.collect(now+timedelta(minutes=10))["new_revisions"] == 1
    records = [json.loads(p.read_text()) for p in (tmp_path / "news").glob('*.json') if p.name != 'status.json']
    assert len(records) == 2
    assert min(r["first_observed_at"] for r in records) == now.isoformat()


def test_news_truncation_is_explicit(tmp_path):
    now = datetime(2026, 11, 3, tzinfo=timezone.utc)
    client = Mock()
    client.news_page.side_effect = [{"news": [], "next_page_token": str(i)} for i in range(3)]
    result = NewsCollector(client, tmp_path).collect(now)
    assert result["truncated"] is True
    assert result["trading_effect"] == "none"
    assert client.news_page.call_count == 3
