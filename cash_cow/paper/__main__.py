"""Usage: python -m cash_cow.paper {check,run,status,stop,report}."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import time

from .client import PaperClient, APIError, TransportError
from .runner import Runner, atomic_json, totals, validate_config
from .news import start_news_worker

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "data/telemetry/paper_v1"


@contextmanager
def exclusive_lock(directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "runner.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another paper runner owns this state") from None
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def status(directory):
    path = directory / "state.json"
    if not path.exists():
        return {"state": "not_started"}
    state = json.loads(path.read_text())
    return {"mode": "paper", "last_event": state.get("last_event"),
            "halt": state.get("halt"), "order_count": len(state["orders"]),
            "session_count": len(state["sessions"]), "stop_requested": (directory / "STOP").exists()}


def write_report(directory, config):
    state = json.loads((directory / "state.json").read_text())
    cash, qty, cost = totals(state, config["capital"])
    rows = ["# Prospective Alpaca paper report", "",
            f"Generated UTC: {datetime.now(timezone.utc).isoformat()}", "",
            f"Strategy: `{config['version']}`; feed: **{config['feed']}**; initial allocation: USD {config['capital']:,.2f}.",
            "", "Paper fills are simulated against market quotes, not real-money executions.", "",
            f"Orders journaled: {len(state['orders'])}; reconciled SPY quantity: {qty:g}; sleeve cash: ${cash:.2f}.",
            f"Cumulative modeled cost overlay: ${cost:.2f}. This is not broker-reported fees.", "",
            "| Session | Attendance | Status | Paper return | Cost-stressed return |",
            "|---|---|---|---:|---:|"]
    for day, s in sorted(state["sessions"].items()):
        attendance = "partial" if s["partial_attendance"] else "from open"
        if s.get("closed") and not s.get("unresolved_at_close"):
            raw = s["closing_nav"] / s["opening_nav"] - 1
            stress = s["closing_stress_nav"] / s["opening_stress_nav"] - 1
            rows.append(f"| {day} | {attendance} | reconciled, flat | {raw:.3%} | {stress:.3%} |")
        else:
            rows.append(f"| {day} | {attendance} | incomplete/unreconciled | unavailable | unavailable |")
    rows += ["", "Full-month metrics are unavailable until exchange-session coverage is audited. Unobserved days are not filled with zero returns.",
             "", "Cost stress adds max($0.40, $0.0035/share) plus 2bp per filled order. It does not establish actual executable costs, queue priority or market impact.",
             "", f"Last runner event: `{state.get('last_event', {}).get('kind', 'none')}`.",
             f"Global halt: `{state.get('halt')}`.", "",
             "Inspect the private journal for signals, source hashes, intended orders, cumulative broker fills and monitoring gaps. Do not publish raw account records.", ""]
    news_status = directory / "news/status.json"
    if news_status.exists():
        news = json.loads(news_status.read_text())
        rows += ["## News context", "", f"Last successful collection: `{news.get('last_success', 'none')}`.",
                 f"Collector error: `{news.get('error')}`; latest window truncated: `{news.get('truncated')}`; coverage gap: `{news.get('coverage_gap')}`.",
                 "Headlines and revisions are private research context. They do not place orders or prove a news-trading edge.", ""]
    target = directory / "REPORT.md"
    target.write_text("\n".join(rows))
    return target


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "run", "status", "stop", "report"))
    parser.add_argument("--once", action="store_true", help="One run tick, including eligible paper orders")
    args = parser.parse_args()
    config = json.loads((ROOT / "configs/paper_v1.json").read_text())
    validate_config(config)
    if args.command == "status":
        print(json.dumps(status(DIRECTORY), indent=2))
        return
    if args.command == "report":
        print(write_report(DIRECTORY, config))
        return
    if args.command == "stop":
        DIRECTORY.mkdir(parents=True, exist_ok=True)
        (DIRECTORY / "STOP").touch()
        print("Stop requested: runner will cancel its orders and flatten during the regular session. Verify status; do not kill it while exposure remains.")
        return
    api = PaperClient()
    if args.command == "check":
        a, c = api.account(), api.clock()
        p, o = api.positions(), api.open_orders()
        asset, quote = api.asset(), api.quote(config["feed"])
        print(json.dumps({"endpoint": "paper-api.alpaca.markets", "account_status": a.get("status"),
                          "trading_blocked": a.get("trading_blocked"), "cash_at_least_capital": float(a["cash"]) >= config["capital"],
                          "positions": len(p), "open_orders": len(o), "market_open": c["is_open"],
                          "next_open": c["next_open"], "SPY_tradable": asset.get("tradable"),
                          "feed": config["feed"], "quote_timestamp": quote.get("t")}, indent=2))
        return
    with exclusive_lock(DIRECTORY):
        runner = Runner(api, config, DIRECTORY)
        atomic_json(DIRECTORY / "process.json", {"pid": os.getpid(), "started_at": datetime.now(timezone.utc).isoformat()})
        def request_stop(*_):
            (DIRECTORY / "STOP").touch()
        signal.signal(signal.SIGTERM, request_stop)
        signal.signal(signal.SIGINT, request_stop)
        news_stop = start_news_worker(DIRECTORY) if not args.once else None
        while True:
            try:
                event = runner.tick()
            except (APIError, TransportError, ValueError, KeyError, TypeError) as error:
                # Avoid printing response bodies, credentials or account payloads.
                reason = str(error) if isinstance(error, (APIError, TransportError, ValueError)) else "Unexpected API schema; inspect adapter"
                event = runner.event("needs_attention", reason=reason, error_type=type(error).__name__)
            print(json.dumps(event), flush=True)
            write_report(DIRECTORY, config)
            if args.once or event["kind"] == "stopped":
                if news_stop:
                    news_stop.set()
                break
            time.sleep(60 if event["kind"] == "market_closed" else config["poll_seconds"])


if __name__ == "__main__":
    main()
