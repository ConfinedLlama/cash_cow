from datetime import datetime, timedelta, timezone
import json
from unittest.mock import Mock

from cash_cow.paper.news import NewsCollector


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
