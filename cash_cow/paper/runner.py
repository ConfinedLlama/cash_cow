"""Persistent, single-account paper runner. Local state is never disposable.

Orders are journaled before submission. An ambiguous submission is looked up by
client ID on subsequent ticks, never blindly retried. A dedicated account and
exact fill/position/cash reconciliation prevent accidental sharing or shorts.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
import hashlib
import json
import math
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from .client import APIError, TransportError, iso, timestamp
from .strategy import signal

NY = ZoneInfo("America/New_York")
TERMINAL = {"filled", "canceled", "expired", "rejected"}


def number(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Nonfinite account/order value")
    return result


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w") as stream:
        os.chmod(temp, 0o600)
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def validate_config(config):
    if config["mode"] != "paper" or config["symbol"] != "SPY" or config["feed"] not in {"iex", "sip"}:
        raise ValueError("Only paper SPY with an explicit IEX/SIP feed is supported")
    for key in ("capital", "allocation", "daily_loss_limit", "total_loss_limit", "max_spread_bps",
                "max_quote_age_seconds", "max_bar_age_seconds", "entry_limit_buffer_bps",
                "entry_timeout_seconds", "flatten_minutes_before_close",
                "entry_cutoff_minutes_before_close", "poll_seconds"):
        if isinstance(config[key], bool) or not 0 < number(config[key]):
            raise ValueError(f"Invalid configuration field: {key}")
    if config["capital"] > 2000 or config["allocation"] > .95:
        raise ValueError("Initial paper allocation may not exceed the registered USD 2,000 cap")
    if not config["flatten_minutes_before_close"] < config["entry_cutoff_minutes_before_close"] < 390:
        raise ValueError("Invalid session cutoffs")
    if config["poll_seconds"] < 5:
        raise ValueError("Polling must be at least five seconds")


def totals(state, capital):
    cash, qty, cost = float(capital), 0.0, 0.0
    for order in state["orders"].values():
        result = order.get("broker")
        if not result:
            continue
        filled = number(result.get("filled_qty", 0))
        requested = number(order["payload"]["qty"])
        if not 0 <= filled <= requested:
            raise ValueError("Invalid cumulative filled quantity")
        if filled:
            price = number(result["filled_avg_price"])
            if price <= 0:
                raise ValueError("Invalid fill price")
            direction = 1 if order["payload"]["side"] == "buy" else -1
            qty += direction * filled
            cash -= direction * filled * price
            # Explicit stress overlay, NOT broker-reported fees or measured slippage.
            cost += max(.40, .0035 * filled) + .0002 * filled * price
    if qty < -1e-6 or cash < -1e-6:
        raise ValueError("Ledger became short or borrowed cash")
    return cash, max(0.0, qty), cost


class Runner:
    def __init__(self, client, config, directory, now=None, decision_provider=None):
        validate_config(config)
        self.api, self.config = client, config
        self.decision_provider = decision_provider
        if config.get("ai") and (not config["ai"]["enabled"] or decision_provider is None):
            raise ValueError("AI trial is not enabled with a configured decision provider")
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        os.chmod(self.directory, 0o700)
        self.path = self.directory / "state.json"
        self.now = now or (lambda: datetime.now(timezone.utc))
        strategy_source = Path(__file__).with_name("strategy.py").read_bytes()
        if config.get("ai"):
            strategy_source += Path(__file__).with_name("ai.py").read_bytes()
        self.fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True).encode() + strategy_source).hexdigest()
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {
            "version": 1, "fingerprint": self.fingerprint, "orders": {}, "sessions": {},
            "account_fingerprint": None, "halt": None,
        }
        if self.state["fingerprint"] != self.fingerprint:
            raise ValueError("Frozen paper config/strategy changed; restore it and reconcile before creating a new trial")

    def save(self):
        atomic_json(self.path, self.state)

    def event(self, kind, **details):
        record = {"at": iso(self.now()), "kind": kind, **details}
        with (self.directory / "events.jsonl").open("a") as stream:
            stream.write(json.dumps(record, allow_nan=False) + "\n")
        self.state["last_event"] = record
        self.save()
        return record

    def bind(self, account, positions, open_orders):
        fingerprint = hashlib.sha256(account["id"].encode()).hexdigest()
        if self.state["account_fingerprint"] is None:
            if positions or open_orders:
                raise ValueError("Initial paper account must have no positions or open orders")
            if number(account["cash"]) < self.config["capital"]:
                raise ValueError("Dedicated paper account needs at least the configured capital")
            self.state["account_fingerprint"] = fingerprint
            self.state["initial_broker_cash"] = number(account["cash"])
            self.state["started_at"] = iso(self.now())
            self.save()
        elif fingerprint != self.state["account_fingerprint"]:
            raise ValueError("Paper account changed; refusing to mix trial histories")

    def sync(self):
        uncertain = False
        for cid, order in self.state["orders"].items():
            if order.get("broker", {}).get("status") in TERMINAL:
                continue
            result = self.api.order(cid)
            if result is None:
                # A durable intent with no definitive response must not be resubmitted.
                uncertain = True
                continue
            self.accept(order, result)
        self.save()
        return not uncertain

    def accept(self, order, result):
        payload = order["payload"]
        for field in ("client_order_id", "symbol", "side", "type", "time_in_force"):
            if result.get(field) != payload[field]:
                raise ValueError("Broker order does not match the durable intent")
        if number(result["qty"]) != number(payload["qty"]):
            raise ValueError("Broker order quantity differs from intent")
        previous = number(order.get("broker", {}).get("filled_qty", 0))
        if number(result.get("filled_qty", 0)) < previous:
            raise ValueError("Cumulative filled quantity regressed")
        if result.get("status") == "filled" and number(result["filled_qty"]) != number(payload["qty"]):
            raise ValueError("Filled status does not match requested quantity")
        order["broker"] = result

    def pending(self):
        return [o for o in self.state["orders"].values() if o.get("broker", {}).get("status") not in TERMINAL]

    def reconcile(self, account, positions, open_orders):
        cash, qty, cost = totals(self.state, self.config["capital"])
        if any(p["symbol"] != "SPY" for p in positions):
            raise ValueError("Unowned position in dedicated paper account")
        actual = sum(number(p["qty"]) for p in positions)
        if abs(actual - qty) > 1e-6:
            raise ValueError("Fill ledger and broker position disagree; wait for consistent reconciliation")
        known = self.state["orders"]
        if any(o["client_order_id"] not in known for o in open_orders):
            raise ValueError("Unowned open order in dedicated paper account")
        expected = self.state["initial_broker_cash"] + cash - self.config["capital"]
        if abs(number(account["cash"]) - expected) > .02:
            raise ValueError("Broker cash differs from fill ledger; reconcile fees, transfers or manual activity")
        return cash, qty, cost

    def submit(self, day, side, qty, reason, quote=None):
        # Fresh clock check immediately before a mutation; day orders submitted
        # after close would otherwise queue for the following trading session.
        clock = self.api.clock()
        broker_now = timestamp(clock["timestamp"])
        if not clock["is_open"] or abs((broker_now-self.now()).total_seconds()) > 30:
            return self.event("needs_attention", reason="Submission blocked by fresh market clock")
        session = self.state["sessions"].get(day)
        if session and timestamp(session["close"]) - broker_now < timedelta(seconds=45):
            return self.event("needs_attention", reason="Too close to closing to submit safely; verify paper inventory")
        if self.pending():
            raise ValueError("Cannot submit while another intent is unresolved")
        current = totals(self.state, self.config["capital"])[1]
        if side == "sell" and not 0 < qty <= current + 1e-8:
            raise ValueError("Sell cannot exceed reconciled long inventory")
        if side == "buy" and (qty != int(qty) or current != 0):
            raise ValueError("Entries require flat inventory and whole shares")
        if qty <= 0:
            raise ValueError("Positive order quantity required")
        suffix = len(self.state["orders"]) + 1
        prefix = "ccai1" if self.config.get("ai") else "ccp1"
        cid = f"{prefix}-{day.replace('-', '')}-{side}-{suffix}"
        payload = {"symbol": "SPY", "side": side, "qty": format(Decimal(str(qty)), 'f'),
                   "type": "limit" if side == "buy" else "market", "time_in_force": "day",
                   "extended_hours": False, "client_order_id": cid}
        if side == "buy":
            price = Decimal(str(quote["ap"])) * (1 + Decimal(str(self.config["entry_limit_buffer_bps"])) / 10000)
            payload["limit_price"] = str(price.quantize(Decimal("0.01"), rounding=ROUND_CEILING))
        order = {"payload": payload, "created_at": iso(self.now()), "day": day,
                 "reason": reason, "reference_quote": quote,
                 "ai_decision_id": self.state.get("active_ai_decision_id")}
        self.state["orders"][cid] = order
        # fsync before the network request: restart can recover the identical ID.
        self.save()
        try:
            self.accept(order, self.api.submit(payload))
        except (APIError, TransportError):
            # Even a 4xx is reconciled by ID instead of generating another entry.
            return self.event("submission_uncertain", client_order_id=cid)
        self.save()
        return self.event("order_submitted", client_order_id=cid, side=side, reason=reason)

    def cancel_pending(self):
        for order in self.pending():
            broker = order.get("broker")
            if broker and broker.get("status") != "pending_cancel":
                try:
                    self.api.cancel(broker["id"])
                except APIError as error:
                    if error.status not in (404, 422):
                        raise
                # Do not presume cancel succeeded or discard partial fills.

    def flatten(self, day, reason):
        if self.pending():
            self.cancel_pending()
            return self.event("waiting_for_cancel", reason=reason)
        qty = totals(self.state, self.config["capital"])[1]
        if qty:
            exits = sum(o["day"] == day and o["payload"]["side"] == "sell" for o in self.state["orders"].values())
            if exits >= 5:
                return self.event("needs_attention", reason="Five exit attempts exhausted; check Alpaca paper dashboard")
            return self.submit(day, "sell", qty, reason)
        return self.event("flat", reason=reason)

    def finish_sessions(self, now, cash, qty, cost):
        for day, session in self.state["sessions"].items():
            if session.get("closed") or now < timestamp(session["close"]):
                continue
            if qty or self.pending():
                session["unresolved_at_close"] = True
                continue
            session.update(closed=True, closing_nav=cash, closing_stress_nav=cash-cost,
                           modeled_costs=cost-session["opening_costs"], closed_recorded_at=iso(now))
        self.save()
        self.export()

    def export(self):
        sessions = []
        for day, s in sorted(self.state["sessions"].items()):
            if s.get("closed") and not s.get("unresolved_at_close"):
                sessions.append({"session_date": day, "opening_nav": s["opening_stress_nav"],
                                 "closing_nav": s["closing_stress_nav"], "external_flow": 0,
                                 "fees": s["modeled_costs"]})
        atomic_json(self.directory / "sessions.json", {
            "mode": "paper", "strategy_id": self.config["version"] + "_cost_stress",
            "cost_basis": "Model: max(USD0.40,0.0035/share) plus 2bp per filled order; not broker fees",
            "coverage": "Only observed reconciled sessions; inspect state for partial attendance and gaps",
            "sessions": sessions,
        })

    def tick(self):
        now = self.now()
        previous_tick = self.state.get("last_tick_at")
        self.state["last_tick_at"] = iso(now)
        clock = self.api.clock()
        if abs((timestamp(clock["timestamp"]) - now).total_seconds()) > 30:
            return self.event("needs_attention", reason="Local/broker clock discrepancy")
        account = self.api.account()
        positions, open_orders = self.api.positions(), self.api.open_orders()
        self.bind(account, positions, open_orders)
        if not self.sync():
            return self.event("needs_attention", reason="Order outcome unknown; no resubmission. Reconcile by client ID.")
        # Re-read after order reconciliation to reduce fill snapshot races.
        account, positions, open_orders = self.api.account(), self.api.positions(), self.api.open_orders()
        cash, qty, cost = self.reconcile(account, positions, open_orders)
        self.finish_sessions(now, cash, qty, cost)
        day = str(now.astimezone(NY).date())
        stopped = (self.directory / "STOP").exists() or day > self.config["end_date"]
        if not clock["is_open"]:
            if qty or self.pending():
                return self.event("needs_attention", reason="Market closed with unresolved exposure; no queued after-hours order")
            return self.event("stopped" if stopped else "market_closed", next_open=clock["next_open"])
        calendar = self.api.calendar(day)
        if len(calendar) != 1:
            return self.event("needs_attention", reason="Missing/ambiguous exchange calendar")
        session_open = datetime.fromisoformat(day + "T" + calendar[0]["open"]).replace(tzinfo=NY)
        close = datetime.fromisoformat(day + "T" + calendar[0]["close"]).replace(tzinfo=NY)
        if not session_open <= now < close:
            return self.event("needs_attention", reason="Clock/calendar disagree on regular session")
        if day not in self.state["sessions"]:
            if qty or self.pending():
                self.state["halt"] = "Overnight exposure must be reconciled before new entries"
                self.save()
                return self.flatten(day, "overnight_exposure")
            self.state["sessions"][day] = {
                "open": iso(session_open), "close": iso(close), "first_seen": iso(now),
                "opening_nav": cash, "opening_stress_nav": cash-cost, "opening_costs": cost,
                "partial_attendance": now > session_open + timedelta(minutes=1), "blocked": None,
            }
        session = self.state["sessions"][day]
        if previous_tick and now - max(timestamp(previous_tick), session_open) > timedelta(seconds=90):
            session["blocked"] = "monitoring_gap"
            session["monitoring_gap_detected_at"] = iso(now)
        if stopped or self.state["halt"]:
            result = self.flatten(day, "stop_requested" if stopped else self.state["halt"])
            if stopped and not qty and not self.pending():
                return self.event("stopped")
            return result
        if now >= close - timedelta(minutes=self.config["flatten_minutes_before_close"]):
            return self.flatten(day, "session_end")
        if account.get("status") != "ACTIVE" or any(account.get(k) for k in ("trading_blocked", "account_blocked", "trade_suspended_by_user")):
            return self.event("needs_attention", reason="Paper account is not active for trading")
        if self.pending():
            for order in self.pending():
                age = (now - timestamp(order["created_at"])).total_seconds()
                if age > self.config["entry_timeout_seconds"]:
                    self.cancel_pending()
                    return self.event("waiting_for_cancel", reason="order_timeout")
            return self.event("waiting_for_fill")
        if session["blocked"]:
            return self.flatten(day, session["blocked"])
        if not qty and now < session_open + timedelta(minutes=35):
            return self.event("warmup")
        try:
            quote = self.api.quote(self.config["feed"])
            bid, ask = number(quote["bp"]), number(quote["ap"])
            age = (now - timestamp(quote["t"])).total_seconds()
            if not 0 < bid <= ask or not -5 <= age <= self.config["max_quote_age_seconds"]:
                raise ValueError("Stale or invalid quote")
        except (ValueError, APIError, TransportError, KeyError):
            session["blocked"] = "stale_or_unavailable_quote"
            return self.flatten(day, "data_failure") if qty else self.event("entry_blocked", reason=session["blocked"])
        nav = cash + qty * bid
        stress_nav = nav - cost
        session["minimum_observed_nav"] = min(session.get("minimum_observed_nav", nav), nav)
        session["last_nav"] = nav
        session["last_stress_nav"] = stress_nav
        if stress_nav <= self.config["capital"] - self.config["total_loss_limit"]:
            self.state["halt"] = "total_loss_limit"
        if stress_nav <= session["opening_stress_nav"] - self.config["daily_loss_limit"]:
            session["blocked"] = "daily_loss_limit"
        self.save()
        if self.state["halt"] or session["blocked"]:
            return self.flatten(day, self.state["halt"] or session["blocked"])
        try:
            bars = self.api.bars(session_open, now, self.config["feed"])
            observed = signal(bars, session_open, now, self.config["max_bar_age_seconds"])
        except (ValueError, KeyError, APIError, TransportError):
            session["blocked"] = "missing_stale_or_invalid_bars"
            return self.flatten(day, "data_failure") if qty else self.event("entry_blocked", reason=session["blocked"])
        if observed.get("bar") != session.get("last_signal_bar"):
            snapshot = {"observed_at": iso(now), "feed": self.config["feed"], "bars": bars}
            key = now.strftime("%Y%m%dT%H%M%SZ")
            atomic_json(self.directory / "bars" / f"{key}.json", snapshot)
            session["last_signal_bar"] = observed.get("bar")
            session["signal_source_sha256"] = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
        self.event("observation", nav=nav, stress_nav=stress_nav, qty=qty, signal=observed)
        if not observed["ready"]:
            return self.event("warmup")
        attempted = any(o["day"] == day and o["payload"]["side"] == "buy" for o in self.state["orders"].values())
        if self.decision_provider and not qty and (attempted or now >= close - timedelta(minutes=self.config["entry_cutoff_minutes_before_close"])):
            return self.event("no_entry")
        if self.decision_provider:
            # Slow model calls run off-thread; risk exits above never wait for AI.
            proposal = self.decision_provider.decide(observed, quote, qty, stress_nav, day)
            if proposal is None:
                return self.event("ai_waiting_or_unavailable")
            self.state["active_ai_decision_id"] = proposal["decision_id"]
            self.event("ai_proposal", **proposal)
            observed = dict(observed,
                            enter=proposal["action"] == "BUY" and proposal["confidence"] >= self.config["ai"]["minimum_entry_confidence"],
                            exit=proposal["action"] == "EXIT")
        if qty:
            return self.flatten(day, "strategy_exit") if observed["exit"] else self.event("holding")
        if attempted or not observed["enter"] or now >= close - timedelta(minutes=self.config["entry_cutoff_minutes_before_close"]):
            return self.event("no_entry")
        if (close-session_open).total_seconds() != 390*60:
            return self.event("entry_blocked", reason="shortened_session")
        if (ask-bid)/((ask+bid)/2)*10000 > self.config["max_spread_bps"]:
            return self.event("entry_blocked", reason="spread_limit")
        asset = self.api.asset()
        if not asset.get("tradable") or asset.get("status") != "active":
            return self.event("entry_blocked", reason="asset_unavailable")
        # Limit-entry sizing is bounded at the actual submitted limit, not a stale midpoint.
        limit = (Decimal(str(ask)) * (1 + Decimal(str(self.config["entry_limit_buffer_bps"])) / 10000)).quantize(Decimal(".01"), rounding=ROUND_CEILING)
        budget = min(self.config["capital"] * self.config["allocation"], stress_nav * self.config["allocation"], number(account["cash"]))
        shares = int((Decimal(str(max(0, budget - 1))) / limit).to_integral_value(rounding=ROUND_FLOOR))
        if not shares:
            return self.event("entry_blocked", reason="insufficient_cash_for_whole_share")
        return self.submit(day, "buy", shares, "ai_proposal" if self.decision_provider else "orb30_vwap", quote)
