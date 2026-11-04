"""Synthetic execution fixtures; none of these results are trading evidence."""
from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest
import requests

from cash_cow.paper.client import APIError, PaperClient, TransportError, iso
from cash_cow.paper.runner import Runner, totals
from cash_cow.paper.strategy import signal
from cash_cow.paper.__main__ import exclusive_lock, write_report

NY = ZoneInfo("America/New_York")
CONFIG = json.loads((Path(__file__).parents[1] / "configs/paper_v1.json").read_text())


def bars_at(start, count=35):
    rows = [{"t": iso(start + timedelta(minutes=i)), "o": 100., "h": 100.5,
             "l": 99.5, "c": 100., "v": 1000} for i in range(count)]
    rows[-1].update(h=101.5, c=101.)
    return rows


class FakeAPI:
    def __init__(self):
        self.now = datetime(2026, 11, 3, 10, 5, 15, tzinfo=NY)
        self.open = self.now.replace(hour=9, minute=30, second=0)
        self.cash, self.qty = 100000., 0.
        self.orders = {}
        self.submissions = []
        self.cancellations = []
        self.lose_response = False
        self.missing_order = False
        self.extra_position = False
        self.stale_quote = False
        self.missing_bar = False
        self.short_day = False
        self.price = 101.

    def account(self):
        return {"id": "test-account-not-real", "cash": str(self.cash), "status": "ACTIVE", "trading_blocked": False}

    def clock(self):
        return {"timestamp": iso(self.now), "is_open": 9 <= self.now.hour < 16,
                "next_open": iso(self.open + timedelta(days=1))}

    def positions(self):
        if self.extra_position:
            return [{"symbol": "QQQ", "qty": "1"}]
        return [{"symbol": "SPY", "qty": str(self.qty)}] if self.qty else []

    def open_orders(self):
        return [deepcopy(o) for o in self.orders.values() if o["status"] in ("new", "partially_filled", "pending_cancel")]

    def order(self, cid):
        return None if self.missing_order else deepcopy(self.orders.get(cid))

    def submit(self, payload):
        self.submissions.append(deepcopy(payload))
        order = dict(payload, id="00000000-0000-0000-0000-000000000001", status="new", filled_qty="0", filled_avg_price=None)
        self.orders[payload["client_order_id"]] = order
        if self.lose_response:
            raise TransportError("Synthetic timeout")
        return deepcopy(order)

    def fill(self, cid, quantity, price=101., status="filled"):
        order = self.orders[cid]
        prior = float(order["filled_qty"])
        delta = quantity - prior
        direction = 1 if order["side"] == "buy" else -1
        self.qty += direction * delta
        self.cash -= direction * delta * price
        order.update(filled_qty=str(quantity), filled_avg_price=str(price), status=status)

    def cancel(self, oid):
        self.cancellations.append(oid)
        for order in self.orders.values():
            if order["id"] == oid:
                order["status"] = "canceled"

    def calendar(self, day):
        return [{"date": day, "open": "09:30", "close": "13:00" if self.short_day else "16:00"}]

    def quote(self, feed):
        return {"bp": self.price, "ap": self.price+.02,
                "t": iso(self.now - timedelta(minutes=5) if self.stale_quote else self.now)}

    def bars(self, start, now, feed):
        count = int((now-start).total_seconds() // 60)
        rows = bars_at(start, count)
        return rows[1:] if self.missing_bar else rows

    def asset(self):
        return {"tradable": True, "status": "active"}


@pytest.fixture
def setup(tmp_path):
    api = FakeAPI()
    runner = Runner(api, CONFIG, tmp_path, now=lambda: api.now)
    return api, runner


def enter_and_fill(api, runner):
    assert runner.tick()["kind"] == "order_submitted"
    payload = api.submissions[-1]
    api.fill(payload["client_order_id"], float(payload["qty"]))
    return payload


def test_only_paper_and_allowlisted_data_urls():
    session = Mock()
    session.request.return_value.status_code = 200
    session.request.return_value.json.return_value = {}
    client = PaperClient(headers={"private": "test"}, session=session)
    client.account()
    args, kwargs = session.request.call_args
    assert args[1] == "https://paper-api.alpaca.markets/v2/account"
    assert kwargs["allow_redirects"] is False
    with pytest.raises(ValueError):
        client.request("POST", "https://api.alpaca.markets/v2/orders")
    with pytest.raises(ValueError):
        client.request("POST", "/v2/orders", data=True)


def test_no_post_transport_retry_or_secret_error():
    session = Mock()
    session.request.side_effect = requests.Timeout("private-secret")
    client = PaperClient(headers={}, session=session)
    with pytest.raises(TransportError) as error:
        client.submit({})
    assert "private-secret" not in str(error.value)
    assert session.request.call_count == 1


def test_http_error_is_sanitized():
    session = Mock()
    session.request.return_value.status_code = 403
    session.request.return_value.text = "private-secret"
    with pytest.raises(APIError) as error:
        PaperClient(headers={}, session=session).account()
    assert "private-secret" not in str(error.value)


def test_causal_signal_and_missing_bar_rejection():
    start = datetime(2026, 11, 3, 9, 30, tzinfo=NY)
    rows = bars_at(start)
    now = start + timedelta(minutes=35)
    assert signal(rows, start, now)["enter"]
    with pytest.raises(ValueError):
        signal(rows, start, now-timedelta(seconds=1))
    with pytest.raises(ValueError):
        signal(rows[1:], start, now)
    with pytest.raises(ValueError):
        signal(rows, start, now+timedelta(minutes=5))


def test_frozen_config_and_account_identity(setup):
    api, runner = setup
    runner.tick()
    changed = dict(CONFIG, allocation=.5)
    with pytest.raises(ValueError, match="Frozen"):
        Runner(api, changed, runner.directory)
    api.account = lambda: {"id": "other", "cash": "100000"}
    with pytest.raises(ValueError, match="account changed"):
        runner.tick()


def test_first_start_refuses_existing_position(setup):
    api, runner = setup
    api.qty = 1
    with pytest.raises(ValueError, match="no positions"):
        runner.tick()
    assert not api.submissions


def test_normal_entry_fills_and_restart_do_not_duplicate(setup):
    api, runner = setup
    payload = enter_and_fill(api, runner)
    assert float(payload["qty"]) * float(payload["limit_price"]) <= 1900
    assert runner.tick()["kind"] == "holding"
    resumed = Runner(api, CONFIG, runner.directory, now=lambda: api.now)
    assert resumed.tick()["kind"] == "holding"
    assert len(api.submissions) == 1


def test_timeout_recovers_by_client_id_without_duplicate(setup):
    api, runner = setup
    api.lose_response = True
    assert runner.tick()["kind"] == "submission_uncertain"
    resumed = Runner(api, CONFIG, runner.directory, now=lambda: api.now)
    assert resumed.tick()["kind"] == "waiting_for_fill"
    assert len(api.submissions) == 1


def test_missing_ambiguous_order_fails_closed(setup):
    api, runner = setup
    api.lose_response = True
    runner.tick()
    api.missing_order = True
    for _ in range(2):
        assert runner.tick()["kind"] == "needs_attention"
    assert len(api.submissions) == 1


def test_partial_entry_cancel_then_exit_only_owned_quantity(setup):
    api, runner = setup
    runner.tick()
    cid = api.submissions[-1]["client_order_id"]
    api.fill(cid, .5, status="partially_filled")
    api.now += timedelta(seconds=65)
    assert runner.tick()["kind"] == "waiting_for_cancel"
    assert api.cancellations
    (runner.directory / "STOP").touch()
    assert runner.tick()["kind"] == "order_submitted"
    assert api.submissions[-1]["side"] == "sell"
    assert float(api.submissions[-1]["qty"]) == .5


@pytest.mark.parametrize("fault", ["stale_quote", "missing_bar", "short_day"])
def test_data_and_calendar_prevent_entries(setup, fault):
    api, runner = setup
    setattr(api, fault, True)
    assert runner.tick()["kind"] == "entry_blocked"
    assert not api.submissions


def test_loss_breaker_flattens_then_blocks_reentry(setup):
    api, runner = setup
    payload = enter_and_fill(api, runner)
    api.price = 95.
    assert runner.tick()["kind"] == "order_submitted"
    exit_order = api.submissions[-1]
    assert exit_order["side"] == "sell"
    api.fill(exit_order["client_order_id"], float(payload["qty"]), price=95.)
    assert runner.tick()["kind"] == "flat"
    assert len(api.submissions) == 2


def test_end_of_day_closes_and_exports_real_fill_ledger(setup):
    api, runner = setup
    payload = enter_and_fill(api, runner)
    api.now = api.now.replace(hour=15, minute=50)
    assert runner.tick()["kind"] == "order_submitted"
    exit_order = api.submissions[-1]
    api.fill(exit_order["client_order_id"], float(payload["qty"]), price=102.)
    api.now = api.now.replace(hour=16, minute=1)
    assert runner.tick()["kind"] == "market_closed"
    report = json.loads((runner.directory / "sessions.json").read_text())
    row = report["sessions"][0]
    cash, qty, cost = totals(runner.state, CONFIG["capital"])
    assert qty == 0
    assert row["closing_nav"] == pytest.approx(cash-cost)
    assert row["fees"] == pytest.approx(cost)
    assert "not broker fees" in report["cost_basis"]
    report_text = write_report(runner.directory, CONFIG).read_text()
    assert "blocked: monitoring_gap" in report_text
    assert "not evidence" in report_text


def test_external_cash_and_manual_positions_halt(setup):
    api, runner = setup
    enter_and_fill(api, runner)
    api.cash += 1
    with pytest.raises(ValueError, match="cash differs"):
        runner.tick()
    assert len(api.submissions) == 1
    api.cash -= 1
    api.extra_position = True
    with pytest.raises(ValueError, match="Unowned"):
        runner.tick()


def test_closed_market_never_queues_orders(setup):
    api, runner = setup
    api.now = api.now.replace(hour=17)
    assert runner.tick()["kind"] == "market_closed"
    assert not api.submissions


def test_stop_marker_exits_cleanly_when_flat(setup):
    api, runner = setup
    (runner.directory / "STOP").touch()
    assert runner.tick()["kind"] == "stopped"
    assert not api.submissions


def test_runner_lock_prevents_concurrent_processes(tmp_path):
    with exclusive_lock(tmp_path):
        with pytest.raises(RuntimeError):
            with exclusive_lock(tmp_path):
                pass


def test_disconnect_with_inventory_blocks_reentry_and_flattens(setup):
    api, runner = setup
    enter_and_fill(api, runner)
    api.now += timedelta(minutes=3)
    result = runner.tick()
    assert result["kind"] == "order_submitted"
    assert result["reason"] == "monitoring_gap"
    assert api.submissions[-1]["side"] == "sell"


def test_last_seconds_do_not_queue_next_day_exit(setup):
    api, runner = setup
    enter_and_fill(api, runner)
    api.now = api.now.replace(hour=15, minute=59, second=50)
    assert runner.tick()["kind"] == "needs_attention"
    assert len(api.submissions) == 1


@pytest.mark.parametrize("update", [{"mode": "live"}, {"capital": 2001}, {"allocation": 1.1}, {"feed": "delayed_sip"}])
def test_unsafe_configuration_rejected(tmp_path, update):
    with pytest.raises(ValueError):
        Runner(FakeAPI(), dict(CONFIG, **update), tmp_path)
