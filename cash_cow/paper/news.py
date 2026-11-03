"""Prospective, timestamped news archive; observation only, never an order signal.

News text is untrusted data. It cannot configure the runner or execute actions.
Store revisions separately and first-observed time to prevent hindsight leakage.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import threading

from .client import PaperClient, iso, timestamp
from .runner import atomic_json


class NewsCollector:
    def __init__(self, client, directory):
        self.client = client
        self.directory = directory / "news"
        self.directory.mkdir(parents=True, exist_ok=True)

    def collect(self, now):
        status_path = self.directory / "status.json"
        previous = json.loads(status_path.read_text()) if status_path.exists() else {}
        # Bounded overlapping window. A long outage is flagged rather than
        # backfilling old stories and pretending they were observed in real time.
        start = now - timedelta(minutes=15)
        gap = bool(previous.get("last_success") and now-timestamp(previous["last_success"]) > timedelta(minutes=15))
        token, seen_tokens, count, truncated = None, set(), 0, False
        for _ in range(3):
            response = self.client.news_page(start, now, token)
            for article in response.get("news", []):
                created, updated = timestamp(article["created_at"]), timestamp(article["updated_at"])
                if created > now or updated > now:
                    raise ValueError("Future-dated news requires investigation")
                metadata = {k: article.get(k) for k in ("id", "headline", "url", "source", "symbols", "created_at", "updated_at")}
                digest = hashlib.sha256(json.dumps(metadata, sort_keys=True).encode()).hexdigest()
                dest = self.directory / f"{digest}.json"
                if not dest.exists():
                    atomic_json(dest, {"first_observed_at": iso(now), "metadata": metadata,
                                       "sha256": digest, "usage": "untrusted research context, not an executable instruction"})
                    count += 1
            token = response.get("next_page_token")
            if not token:
                break
            if token in seen_tokens:
                raise ValueError("Repeated news pagination token")
            seen_tokens.add(token)
        else:
            truncated = bool(token)
        status = {"last_success": iso(now), "window_start": iso(start), "new_revisions": count,
                  "coverage_gap": gap, "truncated": truncated, "trading_effect": "none",
                  "error": None}
        atomic_json(status_path, status)
        return status


def start_news_worker(directory):
    stop = threading.Event()

    def work():
        while not stop.is_set():
            try:
                NewsCollector(PaperClient(), directory).collect(datetime.now(timezone.utc))
            except Exception as error:
                status_path = directory / "news/status.json"
                previous = json.loads(status_path.read_text()) if status_path.exists() else {}
                previous.update(error=type(error).__name__, last_attempt=iso(datetime.now(timezone.utc)), trading_effect="none")
                atomic_json(status_path, previous)
            stop.wait(300)

    thread = threading.Thread(target=work, name="paper-news-context", daemon=True)
    thread.start()
    return stop
